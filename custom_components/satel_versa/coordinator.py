"""Shared polling, availability and bounded reconnect backoff."""

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_DLOADX_ID,
    CONF_ETHM_KEY,
    CONF_INPUTS,
    CONF_PANEL_ID,
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    MAX_RETRY_SECONDS,
)
from .protocol import VersaClient
from .protocol.inputs import InputState

_LOGGER = logging.getLogger(__name__)


def create_client(data: dict, options: dict | None = None) -> VersaClient:
    """Build a private client without exposing credentials in logs."""
    settings = data | (options or {})
    return VersaClient(
        data[CONF_HOST],
        data[CONF_PORT],
        data[CONF_ETHM_KEY].encode("ascii"),
        data[CONF_DLOADX_ID],
        data[CONF_PANEL_ID],
        settings[CONF_INPUTS],
    )


class VersaCoordinator(DataUpdateCoordinator[dict[int, InputState]]):
    """One connection and poll for all configured inputs."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.client = create_client(entry.data, entry.options)
        self._normal_interval = float(
            entry.options.get(
                CONF_POLL_INTERVAL, entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
            )
        )
        self._failures = 0
        self._closing = False
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=self._normal_interval),
            always_update=False,
        )

    async def _async_update_data(self) -> dict[int, InputState]:
        if self._closing:
            raise UpdateFailed("Integration is stopping")
        try:
            if not self.client.connected:
                await self.client.connect()
            states = await self.client.read_inputs()
        except (OSError, TimeoutError, ValueError, EOFError) as err:
            self._failures += 1
            delay = min(MAX_RETRY_SECONDS, max(5, 2 ** min(self._failures, 6)))
            self.update_interval = timedelta(seconds=delay)
            # No raw exception strings: they may contain addresses or protocol data.
            raise UpdateFailed("VERSA connection or response failed") from err
        self._failures = 0
        self.update_interval = timedelta(seconds=self._normal_interval)
        return {state.number: state for state in states}

    async def async_close(self) -> None:
        """Close protocol and socket; repeated calls are harmless."""
        self._closing = True
        try:
            await self.client.close()
        except OSError, TimeoutError, ValueError, EOFError:
            _LOGGER.debug("VERSA session closed without a STOP acknowledgement")
