"""Okos Bojler – tartalék fűtési időablak."""
from __future__ import annotations

from datetime import time as dtime

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import BoilerController, _parse_time
from .entity import BojlerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    ctrl: BoilerController = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            BojlerTime(ctrl, "backup_start", "tartalek_kezdete", "Tartalék fűtés kezdete", "mdi:clock-start"),
            BojlerTime(ctrl, "backup_end", "tartalek_vege", "Tartalék fűtés vége", "mdi:clock-end"),
            BojlerTime(ctrl, "night_start", "ejszaka_kezdete", "Éjszakai tiltás kezdete", "mdi:weather-night"),
            BojlerTime(ctrl, "night_end", "ejszaka_vege", "Éjszakai tiltás vége", "mdi:weather-sunset-up"),
        ]
    )


class BojlerTime(BojlerEntity, TimeEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, ctrl, setting, key, name, icon) -> None:
        super().__init__(ctrl, "time", key, name)
        self._setting = setting
        self._attr_icon = icon

    @property
    def native_value(self) -> dtime | None:
        try:
            return _parse_time(self.ctrl.settings[self._setting])
        except (ValueError, TypeError):
            return None

    async def async_set_value(self, value: dtime) -> None:
        await self.ctrl.async_set_setting(self._setting, value.strftime("%H:%M"))
