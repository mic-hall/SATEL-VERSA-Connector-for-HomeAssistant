"""Minimal diagnostics: omit all credentials, addresses, IDs and input states."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_INPUTS, CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    coordinator = getattr(entry, "runtime_data", None)
    return {
        "integration_version": "0.1.0-beta.1",
        "configured_input_count": len(entry.options.get(CONF_INPUTS, entry.data[CONF_INPUTS])),
        "poll_interval_seconds": entry.options.get(
            CONF_POLL_INTERVAL, entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
        ),
        "last_update_success": coordinator.last_update_success if coordinator else False,
    }
