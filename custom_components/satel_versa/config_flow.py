"""UI setup, reconfiguration and polling options."""

from typing import Any

import probatio as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_DLOADX_ID,
    CONF_ETHM_KEY,
    CONF_INPUTS,
    CONF_PANEL_ID,
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_PORT,
    DOMAIN,
)
from .coordinator import create_client
from .settings import parse_inputs, validate_settings


def connection_schema(defaults: dict | None = None) -> vol.Schema:
    """Never pre-fill or redisplay credentials in the form."""
    defaults = defaults or {}
    password = selector.TextSelector(
        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
    )
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=65535)
            ),
            vol.Required(CONF_ETHM_KEY): password,
            vol.Required(CONF_DLOADX_ID): password,
            vol.Required(CONF_PANEL_ID): password,
            vol.Required(
                CONF_INPUTS, default=",".join(map(str, defaults.get(CONF_INPUTS, [1])))
            ): str,
            vol.Required(
                CONF_POLL_INTERVAL, default=defaults.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
            ): vol.All(vol.Coerce(float), vol.Range(min=1, max=60)),
        }
    )


async def validate_connection(data: dict) -> None:
    """Require one actual input snapshot, always closing the probe session."""
    client = create_client(data)
    try:
        await client.connect()
        await client.read_inputs()
    finally:
        try:
            await client.close()
        except OSError, TimeoutError, ValueError, EOFError:
            pass


class VersaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Add a local panel through the UI."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            try:
                data = validate_settings(user_input)
            except ValueError as err:
                errors["base"] = err.args[0]
            else:
                # Panel ID is user-configurable, but stable across IP/name changes.
                # Changing it later intentionally requires removing/re-adding entry.
                await self.async_set_unique_id(data[CONF_PANEL_ID])
                self._abort_if_unique_id_configured()
                try:
                    await validate_connection(data)
                except OSError, TimeoutError, EOFError:
                    errors["base"] = "cannot_connect"
                except ValueError:
                    errors["base"] = "invalid_response"
                else:
                    return self.async_create_entry(title="SATEL VERSA", data=data)
        return self.async_show_form(step_id="user", data_schema=connection_schema(), errors=errors)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Reconfigure while avoiding a competing session with the running entry."""
        entry = self._get_reconfigure_entry()
        errors = {}
        if user_input is not None:
            try:
                data = validate_settings(user_input)
            except ValueError as err:
                errors["base"] = err.args[0]
            else:
                if data[CONF_PANEL_ID] != entry.unique_id:
                    errors["base"] = "wrong_panel"
                else:
                    was_loaded = entry.state is ConfigEntryState.LOADED
                    if was_loaded and not await self.hass.config_entries.async_unload(
                        entry.entry_id
                    ):
                        errors["base"] = "cannot_unload"
                    else:
                        try:
                            await validate_connection(data)
                        except OSError, TimeoutError, EOFError:
                            errors["base"] = "cannot_connect"
                        except ValueError:
                            errors["base"] = "invalid_response"
                        finally:
                            if errors and was_loaded:
                                await self.hass.config_entries.async_setup(entry.entry_id)
                        if not errors:
                            self.hass.config_entries.async_update_entry(entry, options={})
                            return self.async_update_reload_and_abort(entry, data_updates=data)
        defaults = dict(entry.data) | dict(entry.options)
        return self.async_show_form(
            step_id="reconfigure", data_schema=connection_schema(defaults), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return VersaOptionsFlow()


class VersaOptionsFlow(config_entries.OptionsFlow):
    """Input selection and polling interval; credentials use Reconfigure."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            try:
                inputs = parse_inputs(user_input[CONF_INPUTS])
                interval = float(user_input[CONF_POLL_INTERVAL])
                if not 1 <= interval <= 60:
                    raise ValueError("invalid_interval")
            except ValueError as err:
                errors["base"] = (
                    err.args[0]
                    if err.args[0] in ("invalid_inputs", "invalid_interval")
                    else "invalid_interval"
                )
            else:
                return self.async_create_entry(
                    title="", data={CONF_INPUTS: inputs, CONF_POLL_INTERVAL: interval}
                )
        defaults = dict(self.config_entry.data) | dict(self.config_entry.options)
        schema = vol.Schema(
            {
                vol.Required(CONF_INPUTS, default=",".join(map(str, defaults[CONF_INPUTS]))): str,
                vol.Required(CONF_POLL_INTERVAL, default=defaults[CONF_POLL_INTERVAL]): vol.All(
                    vol.Coerce(float), vol.Range(min=1, max=60)
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
