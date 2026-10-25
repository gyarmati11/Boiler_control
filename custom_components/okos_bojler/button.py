"""Okos Bojler – gombok (turbó, statisztika nullázás)."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import BoilerController
from .entity import BojlerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    ctrl: BoilerController = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            BojlerButton(ctrl, "turbo_inditas", "Turbó indítása", "mdi:rocket-launch",
                         ctrl.async_start_turbo),
            BojlerButton(ctrl, "turbo_leallitas", "Turbó leállítása", "mdi:stop-circle-outline",
                         ctrl.async_stop_turbo),
            BojlerButton(ctrl, "statisztika_nullazas", "Statisztika nullázása", "mdi:restore",
                         ctrl.async_reset_stats, EntityCategory.CONFIG),
        ]
    )


class BojlerButton(BojlerEntity, ButtonEntity):
    def __init__(self, ctrl, key, name, icon, action, category=None) -> None:
        super().__init__(ctrl, "button", key, name)
        self._attr_icon = icon
        self._action = action
        if category:
            self._attr_entity_category = category

    async def async_press(self) -> None:
        await self._action()
