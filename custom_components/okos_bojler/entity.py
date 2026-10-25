"""Okos Bojler – közös entitás alap."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, VERSION
from .coordinator import BoilerController


class BojlerEntity(Entity):
    """Közös alap: eszköz, egyedi azonosító, frissítés."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, ctrl: BoilerController, platform: str, key: str, name: str) -> None:
        self.ctrl = ctrl
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{ctrl.entry.entry_id}_{key}"
        # Kiszámítható entitás azonosító, pl. sensor.okos_bojler_allapot
        self.entity_id = f"{platform}.{ctrl.prefix}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, ctrl.entry.entry_id)},
            name=ctrl.entry.title,
            manufacturer="Okos Bojler",
            model="Napelemes bojlervezérlő",
            sw_version=VERSION,
        )

    async def async_added_to_hass(self) -> None:
        self.ctrl.entity_ids[self._key] = self.entity_id
        self.async_on_remove(self.ctrl.add_listener(self.async_write_ha_state))
