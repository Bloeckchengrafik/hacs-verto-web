"""Backup and battery standby status."""

from homeassistant.components.binary_sensor import BinarySensorEntity

from .entity import VertoEntity, async_discover_entities


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    async_discover_entities(entry.runtime_data, entry, async_add_entities, VertoBinarySensor, True)


class VertoBinarySensor(VertoEntity, BinarySensorEntity):
    """Preserve the boolean flags reported by the inverter."""

    @property
    def is_on(self) -> bool | None:
        reading = self.current_reading
        return reading.value if reading else None
