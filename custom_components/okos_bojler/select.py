"""Okos Bojler – üzemmód választó."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MODES
from .coordinator import BoilerController
from .entity import BojlerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    ctrl: BoilerController = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ModeSelect(ctrl)])


class ModeSelect(BojlerEntity, SelectEntity):
    _attr_icon = "mdi:cog-transfer"
    _attr_options = MODES

    def __init__(self, ctrl: BoilerController) -> None:
        super().__init__(ctrl, "select", "uzemmod", "Üzemmód")

    @property
    def current_option(self) -> str:
        return self.ctrl.settings["mode"]

    async def async_select_option(self, option: str) -> None:
        await self.ctrl.async_set_setting("mode", option)
