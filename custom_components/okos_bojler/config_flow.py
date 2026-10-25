"""Okos Bojler – beállítási varázsló."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .const import CONF_BATTERY, CONF_EV, CONF_NAME, CONF_SWITCH, DOMAIN

SWITCH_SELECTOR = EntitySelector(
    EntitySelectorConfig(domain=["switch", "input_boolean", "light"])
)
BATTERY_SELECTOR = EntitySelector(
    EntitySelectorConfig(domain=["sensor", "input_number", "number"])
)
EV_SELECTOR = EntitySelector(
    EntitySelectorConfig(domain=["binary_sensor", "switch", "input_boolean", "sensor"])
)


class OkosBojlerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_SWITCH])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={
                    CONF_SWITCH: user_input[CONF_SWITCH],
                    CONF_BATTERY: user_input[CONF_BATTERY],
                    CONF_EV: user_input.get(CONF_EV),
                },
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="Okos Bojler"): str,
                vol.Required(CONF_SWITCH): SWITCH_SELECTOR,
                vol.Required(CONF_BATTERY): BATTERY_SELECTOR,
                vol.Optional(CONF_EV): EV_SELECTOR,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OkosBojlerOptionsFlow()


class OkosBojlerOptionsFlow(config_entries.OptionsFlow):
    """Forrás entitások módosítása utólag."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            user_input.setdefault(CONF_EV, None)
            return self.async_create_entry(title="", data=user_input)

        conf = {**self.config_entry.data, **self.config_entry.options}
        schema = vol.Schema(
            {
                vol.Required(CONF_SWITCH, default=conf.get(CONF_SWITCH)): SWITCH_SELECTOR,
                vol.Required(CONF_BATTERY, default=conf.get(CONF_BATTERY)): BATTERY_SELECTOR,
                vol.Optional(
                    CONF_EV, description={"suggested_value": conf.get(CONF_EV)}
                ): EV_SELECTOR,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
