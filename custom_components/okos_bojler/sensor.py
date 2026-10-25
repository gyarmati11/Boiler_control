"""Okos Bojler – szenzorok (állapot, fűtési idők)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, REASONS
from .coordinator import BoilerController
from .entity import BojlerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    ctrl: BoilerController = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            StatusSensor(ctrl),
            HeatTimeSensor(ctrl, "day", "futes_ma", "Fűtés ma", "prev_day", "tegnap_perc"),
            HeatTimeSensor(ctrl, "week", "futes_het", "Fűtés ezen a héten", "prev_week", "elozo_het_perc"),
            HeatTimeSensor(ctrl, "month", "futes_honap", "Fűtés ebben a hónapban", "prev_month", "elozo_honap_perc"),
            HeatTimeSensor(ctrl, "lifetime", "futes_osszes", "Fűtés összesen", None, None),
            RemainingSensor(ctrl, "turbo_hatra", "Turbó hátralévő idő", "mdi:rocket-launch",
                            lambda c: c.turbo_remaining_seconds),
            RemainingSensor(ctrl, "minimum_hatra", "Napi minimumból hátralévő", "mdi:timer-sand",
                            lambda c: c.backup_remaining_seconds),
        ]
    )


class StatusSensor(BojlerEntity, SensorEntity):
    _attr_icon = "mdi:water-boiler"

    def __init__(self, ctrl: BoilerController) -> None:
        super().__init__(ctrl, "sensor", "allapot", "Állapot")

    @property
    def native_value(self) -> str:
        return REASONS.get(self.ctrl.reason, self.ctrl.reason)

    @property
    def icon(self) -> str:
        return "mdi:water-boiler" if self.ctrl.status_attributes()["futes_aktiv"] else "mdi:water-boiler-off"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.ctrl.status_attributes()


class HeatTimeSensor(BojlerEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 0
    _attr_icon = "mdi:timer-outline"

    def __init__(self, ctrl, period, key, name, prev_key, prev_attr) -> None:
        super().__init__(ctrl, "sensor", key, name)
        self._period = period
        self._prev_key = prev_key
        self._prev_attr = prev_attr

    @property
    def native_value(self) -> float:
        return round(self.ctrl.minutes(self._period), 1)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        minutes = self.ctrl.minutes(self._period)
        attrs: dict[str, Any] = {
            "ora": round(minutes / 60, 2),
            "becsult_energia_kwh": self.ctrl.kwh(minutes),
        }
        if self._prev_key:
            prev = self.ctrl.stats[self._prev_key] / 60
            attrs[self._prev_attr] = round(prev, 1)
            attrs["elozo_becsult_energia_kwh"] = self.ctrl.kwh(prev)
        if self._period == "day":
            attrs["bontas_perc"] = self.ctrl.status_attributes()["ma_bontas_perc"]
        return attrs


class RemainingSensor(BojlerEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_suggested_display_precision = 0

    def __init__(self, ctrl, key, name, icon, getter) -> None:
        super().__init__(ctrl, "sensor", key, name)
        self._attr_icon = icon
        self._getter = getter

    @property
    def native_value(self) -> float:
        return round(self._getter(self.ctrl) / 60, 1)
