from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.satel_versa.protocol.outputs import Indicator, OutputIndicator

from .conftest import DATA, FORM


async def setup(hass, mock_client):
    mock_client.read_outputs = AsyncMock(
        return_value=(
            OutputIndicator(1, Indicator.RED, 0x80),
            OutputIndicator(12, Indicator.BLINKING_GREEN_RED, 0x10),
        )
    )
    entry = MockConfigEntry(
        domain="satel_versa", unique_id=DATA["panel_id"], data=DATA | {"outputs": [1, 12]}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def output_id(hass, entry, number):
    return er.async_get(hass).async_get_entity_id(
        "sensor", "satel_versa", f"{entry.unique_id}_output_indicator_{number}"
    )


async def test_output_entities_states_recovery_and_no_private_flags(hass, mock_client):
    entry = await setup(hass, mock_client)
    entity_id = output_id(hass, entry, 1)
    blinking_id = output_id(hass, entry, 12)
    assert hass.states.get(entity_id).state == "red"
    assert hass.states.get(blinking_id).state == "blinking_green_red"
    assert hass.states.get(entity_id).attributes["options"] == [
        "green",
        "red",
        "blinking_green_red",
    ]
    assert "raw_flags" not in hass.states.get(entity_id).attributes
    assert (
        er.async_get(hass).async_get(entity_id).device_id
        == er.async_get(hass)
        .async_get(
            er.async_get(hass).async_get_entity_id(
                "binary_sensor", "satel_versa", f"{entry.unique_id}_input_1"
            )
        )
        .device_id
    )
    coordinator = entry.runtime_data
    mock_client.read_outputs.side_effect = ValueError("bad checksum")
    await coordinator.async_refresh()
    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE
    mock_client.read_outputs.side_effect = None
    mock_client.read_outputs.return_value = (OutputIndicator(1, Indicator.GREEN, 0),)
    await coordinator.async_refresh()
    assert hass.states.get(entity_id).state == "green"
    assert hass.states.get(blinking_id).state == STATE_UNAVAILABLE
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE


async def test_output_selection_reload_removes_entities_and_disables_poll(hass, mock_client):
    entry = await setup(hass, mock_client)
    removed_id = output_id(hass, entry, 12)
    hass.config_entries.async_update_entry(entry, options={"outputs": [1]})
    await hass.async_block_till_done()
    assert er.async_get(hass).async_get(removed_id) is None
    assert output_id(hass, entry, 1) is not None
    mock_client.read_outputs.reset_mock()
    hass.config_entries.async_update_entry(entry, options={"outputs": []})
    await hass.async_block_till_done()
    mock_client.read_outputs.assert_not_awaited()
    assert output_id(hass, entry, 1) is None
    await hass.config_entries.async_unload(entry.entry_id)


async def test_config_probes_requested_outputs_and_cleans_up(hass, mock_client):
    with patch("custom_components.satel_versa.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(
            "satel_versa", context={"source": SOURCE_USER}, data=FORM | {"outputs": "1,12"}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"]["outputs"] == [1, 12]
        mock_client.read_outputs.assert_awaited_once()
        mock_client.close.assert_awaited_once()
        await hass.async_block_till_done()


async def test_invalid_output_probe_keeps_config_form(hass, mock_client):
    mock_client.read_outputs.side_effect = ValueError("unsupported profile")
    result = await hass.config_entries.flow.async_init(
        "satel_versa", context={"source": SOURCE_USER}, data=FORM | {"outputs": "1"}
    )
    assert result["errors"] == {"base": "invalid_response"}
    mock_client.close.assert_awaited_once()


async def test_options_save_output_ranges_and_reject_invalid_positions(hass, mock_client):
    entry = MockConfigEntry(domain="satel_versa", unique_id=DATA["panel_id"], data=DATA)
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"inputs": "1,10", "outputs": "13", "poll_interval": 1}
    )
    assert result["errors"] == {"base": "invalid_outputs"}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"inputs": "1,10", "outputs": "1-3,12", "poll_interval": 1}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["outputs"] == [1, 2, 3, 12]


def test_client_factory_uses_output_options_without_mutating_data():
    from custom_components.satel_versa.coordinator import create_client

    with patch("custom_components.satel_versa.coordinator.VersaClient") as factory:
        create_client(DATA, {"outputs": [1, 12]})
    assert factory.call_args.kwargs["output_numbers"] == [1, 12]
    assert "outputs" not in DATA
