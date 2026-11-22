"""Shared polling, availability and bounded reconnect backoff."""

import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_DLOADX_ID,
    CONF_ETHM_KEY,
    CONF_INPUTS,
    CONF_OUTPUTS,
    CONF_PANEL_ID,
    CONF_PARTITIONS,
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    MAX_RETRY_SECONDS,
)
from .protocol import VersaClient
from .protocol.inputs import InputState
from .protocol.outputs import OutputIndicator
from .protocol.partitions import PartitionState

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
        output_numbers=settings.get(CONF_OUTPUTS, []),
        partition_numbers=settings.get(CONF_PARTITIONS, []),
    )


@dataclass(frozen=True)
class VersaSnapshot:
    inputs: dict[int, InputState]
    outputs: dict[int, OutputIndicator]
    partitions: dict[int, PartitionState]


class VersaCoordinator(DataUpdateCoordinator[VersaSnapshot]):
    """One connection for a complete input and optional output snapshot."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.client = create_client(entry.data, entry.options)
        self._outputs = entry.options.get(CONF_OUTPUTS, entry.data.get(CONF_OUTPUTS, []))
        self._partitions = entry.options.get(CONF_PARTITIONS, entry.data.get(CONF_PARTITIONS, []))
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

    async def _async_update_data(self) -> VersaSnapshot:
        if self._closing:
            raise UpdateFailed("Integration is stopping")
        try:
            if not self.client.connected:
                await self.client.connect()
            states = await self.client.read_inputs()
            outputs = await self.client.read_outputs() if self._outputs else ()
            partitions = await self.client.read_partitions() if self._partitions else ()
        except (OSError, TimeoutError, ValueError, EOFError) as err:
            self._failures += 1
            delay = min(MAX_RETRY_SECONDS, max(5, 2 ** min(self._failures, 6)))
            self.update_interval = timedelta(seconds=delay)
            # No raw exception strings: they may contain addresses or protocol data.
            raise UpdateFailed("VERSA connection or response failed") from err
        self._failures = 0
        self.update_interval = timedelta(seconds=self._normal_interval)
        return VersaSnapshot(
            {state.number: state for state in states},
            {state.number: state for state in outputs},
            {state.number: state for state in partitions},
        )

    async def async_close(self) -> None:
        """Close protocol and socket; repeated calls are harmless."""
        self._closing = True
        try:
            await self.client.close()
        except OSError, TimeoutError, ValueError, EOFError:
            _LOGGER.debug("VERSA session closed without a STOP acknowledgement")
