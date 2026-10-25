"""Okos Bojler – állítható számértékek."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import BoilerController
from .entity import BojlerEntity

# (beállítás kulcs, entitás kulcs, név, min, max, lépés, mértékegység, ikon)
NUMBERS = [
    ("on_threshold", "bekapcsolasi_kuszob", "Akku bekapcsolási küszöb", 10, 100, 1, PERCENTAGE, "mdi:battery-arrow-up"),
    ("off_threshold", "kikapcsolasi_kuszob", "Akku kikapcsolási küszöb", 0, 100, 1, PERCENTAGE, "mdi:battery-arrow-down"),
    ("min_minutes", "napi_minimum", "Napi minimum fűtés", 0, 600, 5, UnitOfTime.MINUTES, "mdi:timer-cog-outline"),
    ("turbo_hours", "turbo_idotartam", "Turbó időtartam", 0.5, 12, 0.5, UnitOfTime.HOURS, "mdi:rocket-launch-outline"),
    ("power_kw", "teljesitmeny", "Bojler teljesítmény", 0.5, 6, 0.1, UnitOfPower.KILO_WATT, "mdi:flash"),
    ("ev_threshold_w", "autotoltes_kuszob", "Autótöltés érzékelési küszöb", 0, 22000, 100, UnitOfPower.WATT, "mdi:ev-plug-type2"),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    ctrl: BoilerController = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(BojlerNumber(ctrl, *n) for n in NUMBERS)


class BojlerNumber(BojlerEntity, NumberEntity):
    _attr_mode = NumberMode.SLIDER
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, ctrl, setting, key, name, vmin, vmax, step, unit, icon) -> None:
        super().__init__(ctrl, "number", key, name)
        self._setting = setting
        self._attr_native_min_value = vmin
        self._attr_native_max_value = vmax
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon

    @property
    def native_value(self) -> float:
        return float(self.ctrl.settings[self._setting])

    async def async_set_native_value(self, value: float) -> None:
        await self.ctrl.async_set_setting(self._setting, float(value))
