"""Read-only SATEL VERSA input states over ETHM-1 Plus."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import HomeAssistant

from .coordinator import VersaCoordinator

PLATFORMS = [Platform.BINARY_SENSOR]
type VersaConfigEntry = ConfigEntry[VersaCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: VersaConfigEntry) -> bool:
    """Set up and test the first poll before adding entities."""
    coordinator = VersaCoordinator(hass, entry)
    try:
        await coordinator.async_config_entry_first_refresh()
    except BaseException:
        await coordinator.async_close()
        raise
    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    async def stop(_event):
        await coordinator.async_close()

    entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop))
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except BaseException:
        await coordinator.async_close()
        raise
    return True


async def async_unload_entry(hass: HomeAssistant, entry: VersaConfigEntry) -> bool:
    """Unload entities, cancel their polling and close the session."""
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.async_close()
        return True
    return False


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Apply changed options or connection settings."""
    await hass.config_entries.async_reload(entry.entry_id)
