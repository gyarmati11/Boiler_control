"""Okos Bojler – napelemes akkumulátor alapú bojler vezérlés."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS, VERSION
from .coordinator import BoilerController

_LOGGER = logging.getLogger(__name__)

CARD_URL = f"/{DOMAIN}/okos-bojler-card.js"


async def _register_frontend(hass: HomeAssistant) -> None:
    """A Lovelace kártya automatikus betöltése (nem kell kézzel erőforrást felvenni)."""
    if hass.data.get(f"{DOMAIN}_frontend") or getattr(hass, "http", None) is None:
        return
    path = str(Path(__file__).parent / "frontend" / "okos-bojler-card.js")
    try:
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, path, False)]
        )
    except ImportError:  # régebbi HA
        hass.http.register_static_path(CARD_URL, path, False)

    try:
        from homeassistant.components.frontend import add_extra_js_url

        add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}")
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("A kártya automatikus betöltése nem sikerült: %s", err)
    hass.data[f"{DOMAIN}_frontend"] = True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await _register_frontend(hass)

    controller = BoilerController(hass, entry)
    await controller.async_setup()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = controller

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        controller: BoilerController = hass.data[DOMAIN].pop(entry.entry_id)
        await controller.async_unload()
    return unload_ok
