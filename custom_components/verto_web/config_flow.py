"""Configure the local web API through the Home Assistant UI."""

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import VertoAuthError, VertoClient, VertoError, normalize_url
from .const import DEFAULT_INTERVAL, DOMAIN


class VertoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Connect without a Solar API password or Modbus."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors = {}
        if user_input is not None:
            try:
                host = normalize_url(user_input[CONF_HOST])
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()
                client = VertoClient(async_get_clientsession(self.hass), host)
                await client.get("powerflow")
            except ValueError:
                errors["base"] = "invalid_host"
            except VertoAuthError:
                errors["base"] = "auth_required"
            except VertoError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title=f"Verto ({host})", data={CONF_HOST: host})
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema({vol.Required(CONF_HOST): str}), errors=errors
        )

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return VertoOptionsFlow()


class VertoOptionsFlow(config_entries.OptionsFlow):
    """Allow a conservative configurable polling interval."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_INTERVAL),
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=300)),
                }
            ),
        )
