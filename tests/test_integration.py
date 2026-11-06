from datetime import timedelta
from unittest.mock import patch

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.satel_versa.diagnostics import async_get_config_entry_diagnostics
from custom_components.satel_versa.protocol.inputs import InputState

from .conftest import DATA


async def setup(hass):
    entry = MockConfigEntry(domain="satel_versa", unique_id=DATA["panel_id"], data=DATA)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_entities_update_unavailable_recover_and_unload(hass, mock_client):
    entry = await setup(hass)
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "binary_sensor", "satel_versa", f"{entry.unique_id}_input_10"
    )
    assert entity_id is not None
    assert hass.states.get(entity_id).state == "on"
    coordinator = entry.runtime_data
    mock_client.read_inputs.side_effect = TimeoutError
    await coordinator.async_refresh()
    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE
    assert coordinator.update_interval >= timedelta(seconds=5)
    mock_client.read_inputs.side_effect = None
    mock_client.read_inputs.return_value = (
        InputState(1, False, False, False, False, False),
        InputState(10, False, False, True, False, False),
    )
    mock_client.connected = False
    await coordinator.async_refresh()
    assert hass.states.get(entity_id).state == "off"  # alarm memory does not mean violation
    assert coordinator.update_interval == timedelta(seconds=1)
    mock_client.connect.assert_awaited()
    assert await hass.config_entries.async_unload(entry.entry_id)
    mock_client.close.assert_awaited()
    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE


async def test_diagnostics_contain_no_settings_or_states(hass, mock_client):
    entry = await setup(hass)
    data = await async_get_config_entry_diagnostics(hass, entry)
    assert set(data) == {
        "integration_version",
        "configured_input_count",
        "poll_interval_seconds",
        "last_update_success",
    }
    assert data["configured_input_count"] == 2
    assert "192.0.2.10" not in str(data)
    assert DATA["ethm_key"] not in str(data)
    await hass.config_entries.async_unload(entry.entry_id)


async def test_failed_first_refresh_closes_session(hass, mock_client):
    mock_client.read_inputs.side_effect = ValueError("Unsupported response")
    entry = MockConfigEntry(domain="satel_versa", unique_id=DATA["panel_id"], data=DATA)
    entry.add_to_hass(hass)
    with patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups") as forward:
        assert not await hass.config_entries.async_setup(entry.entry_id)
    forward.assert_not_called()
    mock_client.close.assert_awaited()


async def test_changed_input_selection_removes_old_entities(hass, mock_client):
    entry = await setup(hass)
    registry = er.async_get(hass)
    old_id = registry.async_get_entity_id(
        "binary_sensor", "satel_versa", f"{entry.unique_id}_input_10"
    )
    assert old_id is not None
    hass.config_entries.async_update_entry(entry, options={"inputs": [1], "poll_interval": 2})
    await hass.async_block_till_done()
    assert registry.async_get(old_id) is None
    assert entry.runtime_data.update_interval == timedelta(seconds=2)
    await hass.config_entries.async_unload(entry.entry_id)
