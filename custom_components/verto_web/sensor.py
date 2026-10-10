"""Power, meter, battery and diagnostic sensors."""

from homeassistant.components.sensor import SensorEntity

from .entity import VertoEntity, async_discover_entities


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    async_discover_entities(entry.runtime_data, entry, async_add_entities, VertoSensor, False)


class VertoSensor(VertoEntity, SensorEntity):
    """Expose explicitly mapped native units and energy statistics."""

    def __init__(self, coordinator, entry, reading) -> None:
        super().__init__(coordinator, entry, reading)
        self._attr_native_unit_of_measurement = reading.unit
        self._attr_device_class = reading.device_class
        self._attr_state_class = reading.state_class

    @property
    def native_value(self):
        reading = self.current_reading
        return reading.value if reading else None
