from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.satel_versa.binary_sensor import PARTITION_FLAGS
from custom_components.satel_versa.coordinator import create_client
from custom_components.satel_versa.protocol.partitions import decode_partitions

from .conftest import DATA, FORM


def states(mode=5, alarms=0):
    body = bytearray(16)
    body[1] = mode
    body[5] = alarms
    return decode_partitions(0x71, body, [1, 2])


async def setup(hass, mock_client):
    mock_client.read_partitions = AsyncMock(return_value=states())
    entry = MockConfigEntry(
        domain="satel_versa", unique_id=DATA["panel_id"], data=DATA | {"partitions": [1, 2]}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def entity_id(hass, entry, domain, number, key):
    return er.async_get(hass).async_get_entity_id(
        domain, "satel_versa", f"{entry.unique_id}_partition_{number}_{key}"
    )


async def test_mode_delays_and_alarm_entities_update_independently(hass, mock_client):
    entry = await setup(hass, mock_client)
    mode_id = entity_id(hass, entry, "sensor", 1, "arm_mode")
    exit_id = entity_id(hass, entry, "binary_sensor", 1, "exit_delay")
    fire_id = entity_id(hass, entry, "binary_sensor", 1, "fire_alarm")
    alarm_id = entity_id(hass, entry, "binary_sensor", 1, "alarm")
    assert hass.states.get(mode_id).state == "full"
    assert hass.states.get(exit_id).state == "off"
    registry = er.async_get(hass)
    for number in (1, 2):
        for key, enabled in PARTITION_FLAGS.items():
            record = registry.async_get(entity_id(hass, entry, "binary_sensor", number, key))
            assert (record.disabled_by is None) == enabled
    # Memory alone must never activate the current fire alarm entity.
    mock_client.read_partitions.return_value = states(1, 8)
    await entry.runtime_data.async_refresh()
    assert hass.states.get(exit_id).state == "on"
    assert hass.states.get(fire_id).state == "off"
    mock_client.read_partitions.return_value = states(5, 128)
    await entry.runtime_data.async_refresh()
    assert hass.states.get(exit_id).state == "off"
    assert hass.states.get(fire_id).state == "on"
    assert hass.states.get(alarm_id).state == "off"
    assert hass.states.get(entity_id(hass, entry, "binary_sensor", 2, "fire_alarm")).state == "off"
    mock_client.read_partitions.return_value = states(0, 64)
    await entry.runtime_data.async_refresh()
    assert hass.states.get(mode_id).state == "disarmed"
    assert hass.states.get(alarm_id).state == "on"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_partition_failure_unavailable_and_recovery(hass, mock_client):
    entry = await setup(hass, mock_client)
    mode_id = entity_id(hass, entry, "sensor", 1, "arm_mode")
    alarm_id = entity_id(hass, entry, "binary_sensor", 1, "alarm")
    mock_client.read_partitions.side_effect = TimeoutError
    await entry.runtime_data.async_refresh()
    assert hass.states.get(mode_id).state == STATE_UNAVAILABLE
    assert hass.states.get(alarm_id).state == STATE_UNAVAILABLE
    mock_client.read_partitions.side_effect = None
    mock_client.read_partitions.return_value = states(0)
    mock_client.connected = False
    await entry.runtime_data.async_refresh()
    assert hass.states.get(mode_id).state == "disarmed"
    mock_client.connect.assert_awaited()
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert hass.states.get(mode_id).state == STATE_UNAVAILABLE


async def test_partition_reload_removes_only_deselected_entities(hass, mock_client):
    entry = await setup(hass, mock_client)
    removed_id = entity_id(hass, entry, "sensor", 1, "arm_mode")
    hass.config_entries.async_update_entry(entry, options={"partitions": [2]})
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    assert registry.async_get(removed_id) is None
    for key in PARTITION_FLAGS:
        assert entity_id(hass, entry, "binary_sensor", 1, key) is None
    assert entity_id(hass, entry, "sensor", 2, "arm_mode") is not None
    assert (
        registry.async_get_entity_id("binary_sensor", "satel_versa", f"{entry.unique_id}_input_1")
        is not None
    )
    mock_client.read_partitions.reset_mock()
    hass.config_entries.async_update_entry(entry, options={"partitions": []})
    await hass.async_block_till_done()
    mock_client.read_partitions.assert_not_awaited()
    assert entity_id(hass, entry, "sensor", 2, "arm_mode") is None
    await hass.config_entries.async_unload(entry.entry_id)


async def test_setup_probes_partitions_and_closes_session(hass, mock_client):
    with patch("custom_components.satel_versa.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(
            "satel_versa", context={"source": SOURCE_USER}, data=FORM | {"partitions": "1-2"}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"]["partitions"] == [1, 2]
        mock_client.read_partitions.assert_awaited_once()
        mock_client.close.assert_awaited_once()
        await hass.async_block_till_done()


async def test_bad_partition_probe_keeps_form(hass, mock_client):
    mock_client.read_partitions.side_effect = ValueError("Unexpected profile")
    result = await hass.config_entries.flow.async_init(
        "satel_versa", context={"source": SOURCE_USER}, data=FORM | {"partitions": "1"}
    )
    assert result["errors"] == {"base": "invalid_response"}
    mock_client.close.assert_awaited_once()


async def test_partition_options_and_defaults(hass, mock_client):
    entry = MockConfigEntry(domain="satel_versa", unique_id=DATA["panel_id"], data=DATA)
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"inputs": "1,10", "partitions": "3", "poll_interval": 1}
    )
    assert result["errors"] == {"base": "invalid_partitions"}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"inputs": "1,10", "partitions": "1,2", "poll_interval": 1}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["partitions"] == [1, 2]
    with patch("custom_components.satel_versa.coordinator.VersaClient") as factory:
        create_client(DATA, {"partitions": [2]})
    assert factory.call_args.kwargs["partition_numbers"] == [2]
