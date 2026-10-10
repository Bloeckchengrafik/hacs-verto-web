"""Use real Home Assistant entity classes for availability and discovery tests."""

from types import SimpleNamespace

import pytest

from custom_components.verto_web.binary_sensor import VertoBinarySensor
from custom_components.verto_web.entity import async_discover_entities
from custom_components.verto_web.model import parse_snapshot
from custom_components.verto_web.sensor import VertoSensor


class Coordinator:
    def __init__(self, data):
        self.data = data
        self.last_update_success = True
        self.client = SimpleNamespace(base_url="http://inverter.local")
        self.listeners = []

    def async_add_listener(self, listener, context=None):
        self.listeners.append(listener)
        return lambda: self.listeners.remove(listener)


def test_entity_availability_and_energy_metadata(payloads):
    coordinator = Coordinator(parse_snapshot(payloads, {}))
    entry = SimpleNamespace(entry_id="example")
    key = ("battery:battery-example", "BAT_ENERGYACTIVE_LIFETIME_CHARGED_F64")
    entity = VertoSensor(coordinator, entry, coordinator.data.readings[key])
    assert entity.available
    assert entity.native_value == pytest.approx(218.935)
    assert entity.native_unit_of_measurement == "kWh"
    assert entity.state_class == "total_increasing"
    assert entity.device_info["via_device"] == ("verto_web", "example:site")
    del coordinator.data.readings[key]
    assert not entity.available and entity.native_value is None
    coordinator.last_update_success = False
    assert not entity.available


def test_binary_false_is_available(payloads):
    coordinator = Coordinator(parse_snapshot(payloads, {}))
    entity = VertoBinarySensor(
        coordinator,
        SimpleNamespace(entry_id="example"),
        coordinator.data.readings["site", "BackupMode"],
    )
    assert entity.available and entity.is_on is False


def test_late_meter_discovery_without_duplicates(payloads):
    meter = payloads.pop("meter")
    coordinator = Coordinator(parse_snapshot(payloads, {}))
    callbacks = []
    entities = []
    entry = SimpleNamespace(entry_id="example", async_on_unload=callbacks.append)
    async_discover_entities(coordinator, entry, entities.extend, VertoSensor, False)
    before = len(entities)
    payloads["meter"] = meter
    coordinator.data = parse_snapshot(payloads, {})
    coordinator.listeners[0]()
    assert len(entities) > before
    count = len(entities)
    coordinator.listeners[0]()
    assert len(entities) == count
    callbacks[0]()
    assert not coordinator.listeners
