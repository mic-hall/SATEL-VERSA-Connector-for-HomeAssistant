"""Experimental output indicators matching DLOADX colors, without switching."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_OUTPUTS, CONF_PARTITIONS, DOMAIN
from .coordinator import VersaCoordinator
from .protocol.outputs import Indicator
from .protocol.partitions import ArmMode

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create only explicitly selected output positions; default is disabled."""
    outputs = entry.options.get(CONF_OUTPUTS, entry.data.get(CONF_OUTPUTS, []))
    partitions = entry.options.get(CONF_PARTITIONS, entry.data.get(CONF_PARTITIONS, []))
    registry = er.async_get(hass)
    wanted = {f"{entry.unique_id}_output_indicator_{number}" for number in outputs}
    wanted.update(f"{entry.unique_id}_partition_{number}_arm_mode" for number in partitions)
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if (
            entity.platform == DOMAIN
            and entity.domain == "sensor"
            and entity.unique_id.startswith(
                (f"{entry.unique_id}_output_indicator_", f"{entry.unique_id}_partition_")
            )
            and entity.unique_id not in wanted
        ):
            registry.async_remove(entity.entity_id)
    async_add_entities(
        [
            *(VersaOutputIndicator(entry.runtime_data, entry, number) for number in outputs),
            *(VersaPartitionMode(entry.runtime_data, entry, number) for number in partitions),
        ]
    )


class VersaOutputIndicator(CoordinatorEntity[VersaCoordinator], SensorEntity):
    """Report the observed indicator, without inferring physical output ON/OFF."""

    _attr_has_entity_name = True
    _attr_translation_key = "output_indicator"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [indicator.value for indicator in Indicator]
    _attr_icon = "mdi:led-on"

    def __init__(self, coordinator: VersaCoordinator, entry: ConfigEntry, number: int):
        super().__init__(coordinator)
        self._number = number
        self._attr_unique_id = f"{entry.unique_id}_output_indicator_{number}"
        self._attr_translation_placeholders = {"number": str(number)}
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id)})

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.coordinator.data is not None
            and self._number in self.coordinator.data.outputs
        )

    @property
    def native_value(self) -> str | None:
        if not self.available:
            return None
        return self.coordinator.data.outputs[self._number].indicator.value


class VersaPartitionMode(CoordinatorEntity[VersaCoordinator], SensorEntity):
    """Arm mode only; entry/exit delay and alarm flags are separate entities."""

    _attr_has_entity_name = True
    _attr_translation_key = "partition_arm_mode"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [mode.value for mode in ArmMode]
    _attr_icon = "mdi:shield-home"

    def __init__(self, coordinator: VersaCoordinator, entry: ConfigEntry, number: int):
        super().__init__(coordinator)
        self._number = number
        self._attr_unique_id = f"{entry.unique_id}_partition_{number}_arm_mode"
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
    def native_value(self) -> str | None:
        if not self.available:
            return None
        return self.coordinator.data.partitions[self._number].arm_mode.value
