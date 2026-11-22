"""Read-only alarm panels derived from the existing partition snapshots."""

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PARTITIONS, DOMAIN
from .coordinator import VersaCoordinator
from .protocol.partitions import ArmMode, PartitionState

PARALLEL_UPDATES = 0


def partition_alarm_state(state: PartitionState) -> AlarmControlPanelState:
    """Current alarms precede entry delay, exit delay and the selected arm mode.

    Memory and ACPO flags are intentionally not treated as current alarms.
    Day-to-home is an integration mapping, not a new protocol arm mode.
    """
    if state.alarm or state.fire_alarm or state.tamper_alarm or state.warning_alarm:
        return AlarmControlPanelState.TRIGGERED
    if state.entry_delay:
        return AlarmControlPanelState.PENDING
    if state.exit_delay:
        return AlarmControlPanelState.ARMING
    return {
        ArmMode.DISARMED: AlarmControlPanelState.DISARMED,
        ArmMode.FULL: AlarmControlPanelState.ARMED_AWAY,
        ArmMode.NIGHT: AlarmControlPanelState.ARMED_NIGHT,
        ArmMode.DAY: AlarmControlPanelState.ARMED_HOME,
    }[state.arm_mode]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add one panel for each selected partition without any additional polling."""
    partitions = entry.options.get(CONF_PARTITIONS, entry.data.get(CONF_PARTITIONS, []))
    registry = er.async_get(hass)
    wanted = {f"{entry.unique_id}_partition_{number}_alarm_panel" for number in partitions}
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if (
            entity.platform == DOMAIN
            and entity.domain == "alarm_control_panel"
            and entity.unique_id.startswith(f"{entry.unique_id}_partition_")
            and entity.unique_id not in wanted
        ):
            registry.async_remove(entity.entity_id)
    async_add_entities(VersaAlarmPanel(entry.runtime_data, entry, number) for number in partitions)


class VersaAlarmPanel(CoordinatorEntity[VersaCoordinator], AlarmControlPanelEntity):
    """Display the alarm state; every control entry point rejects the request."""

    _attr_has_entity_name = True
    _attr_translation_key = "partition_alarm"
    _attr_supported_features = AlarmControlPanelEntityFeature(0)
    _attr_code_format = None
    _attr_code_arm_required = False

    def __init__(self, coordinator: VersaCoordinator, entry: ConfigEntry, number: int):
        super().__init__(coordinator)
        self._number = number
        self._attr_unique_id = f"{entry.unique_id}_partition_{number}_alarm_panel"
        self._attr_translation_placeholders = {"number": str(number)}
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id)})

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.coordinator.data is not None
            and self._number in self.coordinator.data.partitions
        )

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        if not self.available:
            return None
        return partition_alarm_state(self.coordinator.data.partitions[self._number])

    def alarm_disarm(self, code: str | None = None) -> None:
        """Reject synchronous control without touching the protocol client."""
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="read_only")

    # Disarming has no feature flag in HA. Block it explicitly, along with all
    # other sync and async entry points, rather than relying on feature bits.
    alarm_arm_home = alarm_disarm
    alarm_arm_away = alarm_disarm
    alarm_arm_night = alarm_disarm
    alarm_arm_vacation = alarm_disarm
    alarm_arm_custom_bypass = alarm_disarm
    alarm_trigger = alarm_disarm

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Reject asynchronous control without touching the protocol client."""
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="read_only")

    async_alarm_arm_home = async_alarm_disarm
    async_alarm_arm_away = async_alarm_disarm
    async_alarm_arm_night = async_alarm_disarm
    async_alarm_arm_vacation = async_alarm_disarm
    async_alarm_arm_custom_bypass = async_alarm_disarm
    async_alarm_trigger = async_alarm_disarm
