"""Input violation entities; no guessed motion/door semantics."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_INPUTS, DOMAIN
from .coordinator import VersaCoordinator

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create only explicitly configured inputs."""
    inputs = entry.options.get(CONF_INPUTS, entry.data[CONF_INPUTS])
    registry = er.async_get(hass)
    wanted = {f"{entry.unique_id}_input_{number}" for number in inputs}
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if (
            entity.platform == DOMAIN
            and entity.domain == "binary_sensor"
            and entity.unique_id not in wanted
        ):
            registry.async_remove(entity.entity_id)
    async_add_entities(VersaInput(entry.runtime_data, entry, number) for number in inputs)


class VersaInput(CoordinatorEntity[VersaCoordinator], BinarySensorEntity):
    """Current violation, distinct from alarm memory or bypass."""

    _attr_has_entity_name = True
    _attr_translation_key = "input"

    def __init__(self, coordinator: VersaCoordinator, entry: ConfigEntry, number: int):
        super().__init__(coordinator)
        self._number = number
        self._attr_unique_id = f"{entry.unique_id}_input_{number}"
        self._attr_translation_placeholders = {"number": str(number)}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name="SATEL VERSA",
            manufacturer="SATEL",
            model="VERSA via ETHM-1 Plus",
        )

    @property
    def available(self) -> bool:
        return super().available and self._number in (self.coordinator.data or {})

    @property
    def is_on(self) -> bool | None:
        if not self.available:
            return None
        return self.coordinator.data[self._number].violated
