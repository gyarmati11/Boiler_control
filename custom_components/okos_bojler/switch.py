"""Okos Bojler – funkció kapcsolók."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import BoilerController
from .entity import BojlerEntity

SWITCHES = [
    ("solar_enabled", "napelemes_futes", "Napelemes fűtés", "mdi:solar-power-variant"),
    ("backup_enabled", "tartalek_futes", "Tartalék minimum fűtés", "mdi:clock-alert-outline"),
    ("count_solar", "napi_beszamitas", "Napközbeni fűtés beszámítása", "mdi:calculator-variant-outline"),
    ("night_block", "ejszakai_tiltas", "Éjszakai tiltás", "mdi:weather-night"),
    ("ev_block", "autotoltes_tiltas", "Tiltás autótöltés alatt", "mdi:ev-station"),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    ctrl: BoilerController = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(BojlerSwitch(ctrl, *s) for s in SWITCHES)


class BojlerSwitch(BojlerEntity, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, ctrl, setting, key, name, icon) -> None:
        super().__init__(ctrl, "switch", key, name)
        self._setting = setting
        self._attr_icon = icon

    @property
    def is_on(self) -> bool:
        return bool(self.ctrl.settings[self._setting])

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.ctrl.async_set_setting(self._setting, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.ctrl.async_set_setting(self._setting, False)
