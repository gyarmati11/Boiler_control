"""Okos Bojler – vezérlő logika és statisztika."""
from __future__ import annotations

import logging
from datetime import datetime, time as dtime, timedelta
from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

from .const import (
    CONF_BATTERY,
    CONF_EV,
    CONF_SWITCH,
    DEFAULT_SETTINGS,
    DOMAIN,
    HEAT_KEYS,
    MODE_OFF,
    MODE_ON,
    REASONS,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)

TICK_INTERVAL = timedelta(seconds=15)
COMMAND_RETRY_SEC = 30
MAX_DELTA_SEC = 120
EV_ON_STATES = {"on", "charging", "töltés", "toltes", "töltődik", "charge", "true", "active"}


def _empty_day() -> dict[str, float]:
    return {"total": 0.0, **{k: 0.0 for k in HEAT_KEYS}}


def _empty_stats() -> dict[str, Any]:
    return {
        "day_key": None,
        "week_key": None,
        "month_key": None,
        "day": _empty_day(),
        "week": 0.0,
        "month": 0.0,
        "lifetime": 0.0,
        "prev_day": 0.0,
        "prev_week": 0.0,
        "prev_month": 0.0,
    }


def _parse_time(value: str) -> dtime:
    parts = [int(p) for p in str(value).split(":")]
    while len(parts) < 3:
        parts.append(0)
    return dtime(parts[0], parts[1], parts[2])


class BoilerController:
    """A bojler vezérlése: napelemes / tartalék / turbó logika + időmérés."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        conf = {**entry.data, **entry.options}
        self.switch_entity: str = conf[CONF_SWITCH]
        self.battery_entity: str = conf[CONF_BATTERY]
        self.ev_entity: str | None = conf.get(CONF_EV) or None
        self.prefix: str = slugify(entry.title) or DOMAIN

        self.settings: dict[str, Any] = dict(DEFAULT_SETTINGS)
        self.stats: dict[str, Any] = _empty_stats()
        self.turbo_until: datetime | None = None
        self.reason: str = "var"
        self.desired: bool = False
        self.entity_ids: dict[str, str] = {}

        self._solar_latched = False
        self._last_tick: datetime | None = None
        self._last_on = False
        self._last_cmd: bool | None = None
        self._last_cmd_time: datetime | None = None
        self._listeners: list[Callable[[], None]] = []
        self._unsubs: list[Callable[[], None]] = []
        self._store: Store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}")

    # ------------------------------------------------------------------ setup
    async def async_setup(self) -> None:
        data = await self._store.async_load() or {}
        for key, val in (data.get("settings") or {}).items():
            if key in DEFAULT_SETTINGS:
                self.settings[key] = val
        stored_stats = data.get("stats") or {}
        for key in self.stats:
            if key in stored_stats:
                self.stats[key] = stored_stats[key]
        day = _empty_day()
        day.update(self.stats.get("day") or {})
        self.stats["day"] = day

        if data.get("turbo_until"):
            self.turbo_until = dt_util.parse_datetime(data["turbo_until"])
        self._solar_latched = bool(data.get("solar_latched", False))

        now = dt_util.now()
        self._roll_periods(now)
        self._last_on = self._switch_is_on()
        self._last_tick = now

        self._unsubs.append(
            async_track_state_change_event(
                self.hass,
                [e for e in (self.switch_entity, self.battery_entity, self.ev_entity) if e],
                self._on_state_change,
            )
        )
        self._unsubs.append(
            async_track_time_interval(self.hass, self._on_interval, TICK_INTERVAL)
        )
        self._tick()

    async def async_unload(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        self._tick(control=False)
        await self._store.async_save(self._data_to_save())

    # -------------------------------------------------------------- listeners
    def add_listener(self, cb: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(cb)

        def _remove() -> None:
            if cb in self._listeners:
                self._listeners.remove(cb)

        return _remove

    @callback
    def _notify(self) -> None:
        for cb in list(self._listeners):
            cb()

    @callback
    def _on_state_change(self, event: Event) -> None:
        self._tick()

    @callback
    def _on_interval(self, now: datetime) -> None:
        self._tick()

    # ------------------------------------------------------------------ core
    @callback
    def _tick(self, control: bool = True) -> None:
        now = dt_util.now()
        if self._last_tick is not None and self._last_on:
            delta = (now - self._last_tick).total_seconds()
            delta = max(0.0, min(delta, MAX_DELTA_SEC))
            self._add_time(now, delta)
        else:
            self._roll_periods(now)
        self._last_tick = now

        if control:
            self._evaluate(now)
        self._last_on = self._switch_is_on()
        self._store.async_delay_save(self._data_to_save, 60)
        self._notify()

    def _accounting_key(self) -> str:
        return self.reason if self.reason in HEAT_KEYS else "egyeb"

    def _add_time(self, now: datetime, delta: float) -> None:
        self._roll_periods(now)
        key = self._accounting_key()
        day = self.stats["day"]
        day["total"] += delta
        day[key] = day.get(key, 0.0) + delta
        self.stats["week"] += delta
        self.stats["month"] += delta
        self.stats["lifetime"] += delta

    def _roll_periods(self, now: datetime) -> None:
        day_key = now.date().isoformat()
        iso = now.isocalendar()
        week_key = f"{iso[0]}-W{iso[1]:02d}"
        month_key = now.strftime("%Y-%m")
        s = self.stats
        if s["day_key"] != day_key:
            if s["day_key"] is not None:
                s["prev_day"] = s["day"]["total"]
            s["day_key"] = day_key
            s["day"] = _empty_day()
        if s["week_key"] != week_key:
            if s["week_key"] is not None:
                s["prev_week"] = s["week"]
            s["week_key"] = week_key
            s["week"] = 0.0
        if s["month_key"] != month_key:
            if s["month_key"] is not None:
                s["prev_month"] = s["month"]
            s["month_key"] = month_key
            s["month"] = 0.0

    # ------------------------------------------------------------- decisions
    def _switch_is_on(self) -> bool:
        st = self.hass.states.get(self.switch_entity)
        return st is not None and st.state == STATE_ON

    @property
    def switch_available(self) -> bool:
        st = self.hass.states.get(self.switch_entity)
        return st is not None and st.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN)

    @property
    def battery_level(self) -> float | None:
        st = self.hass.states.get(self.battery_entity)
        if st is None:
            return None
        try:
            return float(st.state)
        except (TypeError, ValueError):
            return None

    def in_backup_window(self, now: datetime | None = None) -> bool:
        return self._in_window("backup_start", "backup_end", now)

    def in_night_window(self, now: datetime | None = None) -> bool:
        return self._in_window("night_start", "night_end", now)

    @property
    def night_blocked(self) -> bool:
        return bool(self.settings["night_block"]) and self.in_night_window()

    @property
    def ev_charging(self) -> bool:
        """Megy-e az autótöltés (kapcsoló/bináris szenzor 'on', teljesítmény > küszöb, vagy 'charging')."""
        if not self.ev_entity:
            return False
        st = self.hass.states.get(self.ev_entity)
        if st is None or st.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return False
        value = str(st.state).strip().lower()
        if value in EV_ON_STATES:
            return True
        try:
            power = float(value)
        except ValueError:
            return False
        unit = str(st.attributes.get("unit_of_measurement", "")).lower()
        if unit == "kw":
            power *= 1000
        return power > float(self.settings["ev_threshold_w"])

    @property
    def ev_blocked(self) -> bool:
        return bool(self.settings["ev_block"]) and self.ev_charging

    def _in_window(self, start_key: str, end_key: str, now: datetime | None = None) -> bool:
        now = now or dt_util.now()
        try:
            start = _parse_time(self.settings[start_key])
            end = _parse_time(self.settings[end_key])
        except (ValueError, TypeError):
            return False
        t = now.time()
        if start == end:
            return False
        if start < end:
            return start <= t < end
        return t >= start or t < end

    @property
    def counted_today_seconds(self) -> float:
        day = self.stats["day"]
        if self.settings["count_solar"]:
            return day["total"]
        return max(0.0, day["total"] - day.get("napelem", 0.0))

    @property
    def backup_remaining_seconds(self) -> float:
        return max(0.0, float(self.settings["min_minutes"]) * 60 - self.counted_today_seconds)

    @property
    def turbo_active(self) -> bool:
        return self.turbo_until is not None and dt_util.now() < self.turbo_until

    @property
    def turbo_remaining_seconds(self) -> float:
        if not self.turbo_active:
            return 0.0
        return max(0.0, (self.turbo_until - dt_util.now()).total_seconds())

    def _decide(self, now: datetime) -> tuple[bool, str]:
        s = self.settings
        if self.turbo_until is not None and now >= self.turbo_until:
            self.turbo_until = None

        if s["mode"] == MODE_OFF:
            return False, "kikapcsolva"
        if s["mode"] == MODE_ON:
            # A "Mindig be" kézi felülbírálás, a tiltások erre nem vonatkoznak
            return True, "turbo" if self.turbo_until is not None else "kezi"

        # Tiltások: éjszaka és autótöltés alatt semmi nem fűt (turbó sem)
        if s["ev_block"] and self.ev_charging:
            self._solar_latched = False
            return False, "autotoltes"
        if s["night_block"] and self.in_night_window(now):
            self._solar_latched = False
            return False, "ejszaka"

        if self.turbo_until is not None:
            return True, "turbo"

        # Napelemes fűtés hiszterézissel
        battery = self.battery_level
        on_th = float(s["on_threshold"])
        off_th = min(float(s["off_threshold"]), on_th)
        if s["solar_enabled"] and battery is not None:
            if battery >= on_th:
                self._solar_latched = True
            elif battery < off_th:
                self._solar_latched = False
            if self._solar_latched:
                return True, "napelem"
        else:
            self._solar_latched = False

        # Tartalék (minimum) fűtés a beállított időablakban
        if s["backup_enabled"] and self.in_backup_window(now):
            if self.backup_remaining_seconds > 0:
                return True, "tartalek"
            return False, "teljesitve"
        if s["backup_enabled"] and self.backup_remaining_seconds <= 0:
            return False, "teljesitve"
        return False, "var"

    def _evaluate(self, now: datetime) -> None:
        desired, reason = self._decide(now)
        self.desired = desired
        self.reason = reason

        st = self.hass.states.get(self.switch_entity)
        if st is None or st.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return
        actual = st.state == STATE_ON
        if actual == desired:
            self._last_cmd = None
            return
        if (
            self._last_cmd == desired
            and self._last_cmd_time is not None
            and (now - self._last_cmd_time).total_seconds() < COMMAND_RETRY_SEC
        ):
            return
        self._last_cmd = desired
        self._last_cmd_time = now
        _LOGGER.debug("Bojler %s (%s)", "BE" if desired else "KI", REASONS.get(reason))
        self.hass.async_create_task(
            self.hass.services.async_call(
                "homeassistant",
                "turn_on" if desired else "turn_off",
                {"entity_id": self.switch_entity},
                blocking=False,
            )
        )

    # --------------------------------------------------------------- actions
    async def async_set_setting(self, key: str, value: Any) -> None:
        if key not in DEFAULT_SETTINGS:
            raise KeyError(key)
        self.settings[key] = value
        self._last_cmd = None
        self._tick()
        await self._store.async_save(self._data_to_save())

    async def async_start_turbo(self) -> None:
        hours = float(self.settings["turbo_hours"])
        self.turbo_until = dt_util.now() + timedelta(hours=hours)
        self._last_cmd = None
        self._tick()
        await self._store.async_save(self._data_to_save())

    async def async_stop_turbo(self) -> None:
        self.turbo_until = None
        self._last_cmd = None
        self._tick()
        await self._store.async_save(self._data_to_save())

    async def async_reset_stats(self) -> None:
        self.stats = _empty_stats()
        self._roll_periods(dt_util.now())
        self._tick()
        await self._store.async_save(self._data_to_save())

    # --------------------------------------------------------------- export
    def _data_to_save(self) -> dict[str, Any]:
        return {
            "settings": self.settings,
            "stats": self.stats,
            "turbo_until": self.turbo_until.isoformat() if self.turbo_until else None,
            "solar_latched": self._solar_latched,
        }

    def minutes(self, period: str) -> float:
        s = self.stats
        if period == "day":
            return s["day"]["total"] / 60
        if period == "week":
            return s["week"] / 60
        if period == "month":
            return s["month"] / 60
        if period == "lifetime":
            return s["lifetime"] / 60
        return 0.0

    def kwh(self, minutes: float) -> float:
        return round(minutes / 60 * float(self.settings["power_kw"]), 2)

    def status_attributes(self) -> dict[str, Any]:
        s = self.settings
        st = self.stats
        day = st["day"]
        return {
            "okos_bojler": True,
            "allapot_kulcs": self.reason,
            "futes_aktiv": self._switch_is_on(),
            "kivant_allapot": self.desired,
            "kapcsolo_elerheto": self.switch_available,
            "akkumulator": self.battery_level,
            "uzemmod": s["mode"],
            "bekapcsolasi_kuszob": s["on_threshold"],
            "kikapcsolasi_kuszob": s["off_threshold"],
            "napelemes_futes": s["solar_enabled"],
            "tartalek_futes": s["backup_enabled"],
            "napi_beszamitas": s["count_solar"],
            "tartalek_kezdete": s["backup_start"],
            "tartalek_vege": s["backup_end"],
            "tartalek_ablakban": self.in_backup_window(),
            "napi_minimum_perc": s["min_minutes"],
            "beszamitott_ma_perc": round(self.counted_today_seconds / 60, 1),
            "minimumbol_hatra_perc": round(self.backup_remaining_seconds / 60, 1),
            "ejszakai_tiltas": s["night_block"],
            "ejszaka_kezdete": s["night_start"],
            "ejszaka_vege": s["night_end"],
            "ejszakai_tiltas_aktiv": self.night_blocked,
            "autotoltes_tiltas": s["ev_block"],
            "autotoltes_kuszob_w": s["ev_threshold_w"],
            "autotolto": self.ev_entity,
            "autotoltes_folyamatban": self.ev_charging,
            "autotoltes_tiltas_aktiv": self.ev_blocked,
            "turbo_aktiv": self.turbo_active,
            "turbo_vege": self.turbo_until.isoformat() if self.turbo_active else None,
            "turbo_hatra_perc": round(self.turbo_remaining_seconds / 60, 1),
            "turbo_ora": s["turbo_hours"],
            "teljesitmeny_kw": s["power_kw"],
            "ma_perc": round(self.minutes("day"), 1),
            "het_perc": round(self.minutes("week"), 1),
            "honap_perc": round(self.minutes("month"), 1),
            "osszes_perc": round(self.minutes("lifetime"), 1),
            "tegnap_perc": round(st["prev_day"] / 60, 1),
            "elozo_het_perc": round(st["prev_week"] / 60, 1),
            "elozo_honap_perc": round(st["prev_month"] / 60, 1),
            "ma_bontas_perc": {k: round(day.get(k, 0.0) / 60, 1) for k in HEAT_KEYS},
            "kapcsolo": self.switch_entity,
            "akku_szenzor": self.battery_entity,
            "entities": dict(self.entity_ids),
        }
