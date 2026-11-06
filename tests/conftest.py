"""HA fixtures; socket access stays blocked by the HA test harness."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.satel_versa.protocol import VersaClient
from custom_components.satel_versa.protocol.inputs import InputState

DATA = {
    "host": "192.0.2.10",
    "port": 7090,
    "ethm_key": "example-only",
    "dloadx_id": "01020304",
    "panel_id": "AABBCCDD",
    "inputs": [1, 10],
    "poll_interval": 1,
}
FORM = DATA | {"inputs": "1,10"}


@pytest.fixture(autouse=True)
def enable_custom_integrations_fixture(enable_custom_integrations):
    """Enable loading our custom component in HA."""
    yield


@pytest.fixture
def mock_client():
    client = MagicMock(spec=VersaClient)
    client.connected = True
    client.connect = AsyncMock()
    client.close = AsyncMock()
    client.read_inputs = AsyncMock(
        return_value=(
            InputState(1, False, False, False, False, False),
            InputState(10, False, True, False, False, False),
        )
    )
    with (
        patch("custom_components.satel_versa.coordinator.create_client", return_value=client),
        patch("custom_components.satel_versa.config_flow.create_client", return_value=client),
    ):
        yield client
