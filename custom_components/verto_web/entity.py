"""Common device information and availability handling."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .model import Reading


class VertoEntity(CoordinatorEntity):
    """An entity backed by one reading in the shared snapshot."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, reading: Reading) -> None:
        super().__init__(coordinator)
        self.reading_key = (reading.device, reading.key)
        self._attr_unique_id = f"{entry.entry_id}:{reading.device}:{reading.key}"
        self._attr_name = reading.name
        self._attr_entity_registry_enabled_default = reading.enabled
        if reading.diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        info = coordinator.data.devices[reading.device]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}:{reading.device}")},
            configuration_url=coordinator.client.base_url,
            **{key: value for key, value in info.items() if value is not None},
        )
        if reading.device != "site":
            self._attr_device_info["via_device"] = (DOMAIN, f"{entry.entry_id}:site")

    @property
    def current_reading(self) -> Reading | None:
        return self.coordinator.data.readings.get(self.reading_key)

    @property
    def available(self) -> bool:
        reading = self.current_reading
        return super().available and reading is not None and reading.value is not None


def async_discover_entities(coordinator, entry, async_add_entities, entity_type, binary: bool):
    """Discover late-arriving channels and components without an HA restart."""
    known = set()

    def discover():
        entities = []
        for key, reading in coordinator.data.readings.items():
            if key not in known and reading.binary == binary:
                known.add(key)
                entities.append(entity_type(coordinator, entry, reading))
        if entities:
            async_add_entities(entities)

    discover()
    entry.async_on_unload(coordinator.async_add_listener(discover))
