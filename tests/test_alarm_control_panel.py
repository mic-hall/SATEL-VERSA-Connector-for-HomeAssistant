from dataclasses import replace
from unittest.mock import AsyncMock

import pytest
from homeassistant.components.alarm_control_panel import AlarmControlPanelState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.satel_versa.alarm_control_panel import (
    VersaAlarmPanel,
    partition_alarm_state,
)
from custom_components.satel_versa.protocol.partitions import ArmMode, decode_partitions

from .conftest import DATA


def partition(**changes):
    body = bytearray(16)
    body[1] = 5
    return replace(decode_partitions(0x71, body, [1])[0], **changes)


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"arm_mode": ArmMode.DISARMED}, AlarmControlPanelState.DISARMED),
        ({"arm_mode": ArmMode.FULL}, AlarmControlPanelState.ARMED_AWAY),
        ({"arm_mode": ArmMode.NIGHT}, AlarmControlPanelState.ARMED_NIGHT),
        ({"arm_mode": ArmMode.DAY}, AlarmControlPanelState.ARMED_HOME),
        ({"exit_delay": True}, AlarmControlPanelState.ARMING),
        ({"entry_delay": True, "exit_delay": True}, AlarmControlPanelState.PENDING),
        ({"alarm": True, "entry_delay": True}, AlarmControlPanelState.TRIGGERED),
        ({"fire_alarm": True, "arm_mode": ArmMode.DISARMED}, AlarmControlPanelState.TRIGGERED),
        ({"tamper_alarm": True, "exit_delay": True}, AlarmControlPanelState.TRIGGERED),
        ({"warning_alarm": True}, AlarmControlPanelState.TRIGGERED),
        (
            {
                "arm_mode": ArmMode.DISARMED,
                "alarm_memory": True,
                "fire_alarm_memory": True,
                "silent_alarm_memory": True,
                "tamper_alarm_memory": True,
                "verified_alarm": True,
                "acpo_blocked": True,
            },
            AlarmControlPanelState.DISARMED,
        ),
        ({"fire_alarm_memory": True, "entry_delay": True}, AlarmControlPanelState.PENDING),
    ],
)
def test_state_mapping_and_priority(changes, expected):
    assert partition_alarm_state(partition(**changes)) is expected


async def setup(hass, mock_client, partitions=None):
    mock_client.read_partitions = AsyncMock(
        return_value=(partition(), partition(number=2, arm_mode=ArmMode.DISARMED))
    )
    entry = MockConfigEntry(
        domain="satel_versa",
        unique_id=DATA["panel_id"],
        data=DATA | {"partitions": [1, 2] if partitions is None else partitions},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def panel_id(hass, entry, number):
    return er.async_get(hass).async_get_entity_id(
        "alarm_control_panel", "satel_versa", f"{entry.unique_id}_partition_{number}_alarm_panel"
    )


async def test_panel_updates_unavailable_recovery_and_unload(hass, mock_client):
    entry = await setup(hass, mock_client)
    first, second = panel_id(hass, entry, 1), panel_id(hass, entry, 2)
    assert hass.states.get(first).state == "armed_away"
    assert hass.states.get(second).state == "disarmed"
    assert hass.states.get(first).attributes["supported_features"] == 0
    assert hass.states.get(first).attributes["code_format"] is None
    assert hass.states.get(first).attributes["changed_by"] is None
    registry = er.async_get(hass)
    mode_id = registry.async_get_entity_id(
        "sensor", "satel_versa", f"{entry.unique_id}_partition_1_arm_mode"
    )
    assert registry.async_get(first).device_id == registry.async_get(mode_id).device_id
    # The panel adds no polling; this is the coordinator's first read.
    mock_client.read_partitions.assert_awaited_once()
    for state, expected in [
        (partition(exit_delay=True), "arming"),
        (partition(entry_delay=True), "pending"),
        (partition(fire_alarm=True, entry_delay=True), "triggered"),
        (partition(arm_mode=ArmMode.DISARMED, fire_alarm_memory=True), "disarmed"),
    ]:
        mock_client.read_partitions.return_value = (state,)
        await entry.runtime_data.async_refresh()
        assert hass.states.get(first).state == expected
        assert hass.states.get(second).state == STATE_UNAVAILABLE
    mock_client.read_partitions.side_effect = TimeoutError
    await entry.runtime_data.async_refresh()
    assert hass.states.get(first).state == STATE_UNAVAILABLE
    mock_client.read_partitions.side_effect = None
    mock_client.read_partitions.return_value = (partition(arm_mode=ArmMode.NIGHT),)
    await entry.runtime_data.async_refresh()
    assert hass.states.get(first).state == "armed_night"
    await hass.config_entries.async_unload(entry.entry_id)
    assert hass.states.get(first).state == STATE_UNAVAILABLE


async def test_partition_selection_and_legacy_entries(hass, mock_client):
    entry = await setup(hass, mock_client)
    first = panel_id(hass, entry, 1)
    hass.config_entries.async_update_entry(entry, options={"partitions": [2]})
    await hass.async_block_till_done()
    assert er.async_get(hass).async_get(first) is None
    assert panel_id(hass, entry, 2) is not None
    hass.config_entries.async_update_entry(entry, options={"partitions": []})
    await hass.async_block_till_done()
    assert panel_id(hass, entry, 2) is None
    await hass.config_entries.async_unload(entry.entry_id)


CONTROL_METHODS = [
    "alarm_disarm",
    "alarm_arm_home",
    "alarm_arm_away",
    "alarm_arm_night",
    "alarm_arm_vacation",
    "alarm_arm_custom_bypass",
    "alarm_trigger",
]


async def test_all_sync_async_and_service_controls_are_read_only(hass, mock_client):
    entry = await setup(hass, mock_client)
    entity = VersaAlarmPanel(entry.runtime_data, entry, 1)
    before = list(mock_client.mock_calls)
    for method in CONTROL_METHODS:
        with pytest.raises(ServiceValidationError) as error:
            getattr(entity, method)(code="1234")
        assert error.value.translation_key == "read_only"
        with pytest.raises(ServiceValidationError) as error:
            await getattr(entity, f"async_{method}")(code="1234")
        assert error.value.translation_key == "read_only"
        # Use actual registered HA actions too; feature checks may reject arm
        # actions first, but disarm must reach our explicit read-only guard.
        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(
                "alarm_control_panel",
                method,
                {"entity_id": panel_id(hass, entry, 1), "code": "1234"},
                blocking=True,
            )
    assert mock_client.mock_calls == before
    assert hass.states.get(panel_id(hass, entry, 1)).state == "armed_away"
    await hass.config_entries.async_unload(entry.entry_id)
