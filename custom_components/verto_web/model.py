"""Pure payload mapping, with explicit channel units and sign conventions."""

import math
from dataclasses import dataclass, field
from typing import Any

from .api import decode_nameplate


@dataclass(frozen=True)
class Reading:
    device: str
    key: str
    name: str
    value: float | str | bool | None
    unit: str | None = None
    device_class: str | None = None
    state_class: str | None = None
    diagnostic: bool = False
    enabled: bool = True
    binary: bool = False


@dataclass
class Snapshot:
    readings: dict[tuple[str, str], Reading] = field(default_factory=dict)
    devices: dict[str, dict[str, Any]] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)


def number(value: Any) -> float | None:
    """Preserve missing values rather than manufacturing zero measurements."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def parse_snapshot(payloads: dict[str, Any], errors: dict[str, str]) -> Snapshot:
    """Map discovered components without assuming fixed meter or battery IDs."""
    result = Snapshot(errors=errors)
    result.devices["site"] = {"name": "Fronius Verto", "manufacturer": "Fronius", "model": "Verto"}

    def add(
        device: str,
        key: str,
        name: str,
        value: Any,
        unit: str | None = None,
        device_class: str | None = None,
        state_class: str | None = "measurement",
        scale: float = 1,
        diagnostic: bool = False,
        enabled: bool = True,
        binary: bool = False,
    ) -> None:
        if binary:
            value = value if isinstance(value, bool) else None
        elif unit is not None or state_class is not None:
            value = number(value)
            if value is not None:
                value *= scale
        reading = Reading(
            device, key, name, value, unit, device_class, state_class, diagnostic, enabled, binary
        )
        result.readings[(device, key)] = reading

    flow = payloads["powerflow"]
    site = flow["site"]
    for key, name in (
        ("P_PV", "PV power"),
        ("P_Grid", "Grid power"),
        ("P_Akku", "Battery power"),
        ("P_Load", "Load power"),
    ):
        if key in site:
            add("site", key, name, site[key], "W", "power", scale=-1 if key == "P_Load" else 1)
    for source, names in (
        ("P_Grid", ("Grid import power", "Grid export power")),
        ("P_Akku", ("Battery discharge power", "Battery charge power")),
    ):
        if source in site:
            value = number(site[source])
            for index, name in enumerate(names):
                add(
                    "site",
                    f"{source}_{index}",
                    name,
                    None if value is None else max(value * (1 if index == 0 else -1), 0),
                    "W",
                    "power",
                )
    for key, name in (("rel_Autonomy", "Autonomy"), ("rel_SelfConsumption", "Self consumption")):
        if key in site:
            add("site", key, name, site[key], "%")
    for key, name in (("BackupMode", "Backup mode"), ("BatteryStandby", "Battery standby")):
        if key in site:
            add("site", key, name, site[key], state_class=None, binary=True)
    if "E_Total" in site:
        add(
            "site",
            "E_Total",
            "Inverter AC energy total",
            site["E_Total"],
            "kWh",
            "energy",
            "total_increasing",
            scale=0.001,
            enabled=False,
        )
    for inverter in flow.get("inverters", []):
        if not isinstance(inverter, dict) or "ID" not in inverter:
            continue
        device = f"inverter:{inverter['ID']}"
        result.devices[device] = {
            "name": f"Verto inverter {inverter['ID']}",
            "manufacturer": "Fronius",
        }
        for key, name, unit, device_class in (
            ("P", "AC power", "W", "power"),
            ("SOC", "State of charge", "%", "battery"),
        ):
            if key in inverter:
                add(device, key, name, inverter[key], unit, device_class)

    for endpoint, prefix in (("meter", "meter"), ("battery", "battery")):
        components = payloads.get(endpoint, {}).get("Body", {}).get("Data", {})
        for component_id, component in components.items():
            attrs = component.get("attributes", {})
            attrs = attrs if isinstance(attrs, dict) else {}
            channels = component["channels"]
            device = f"{prefix}:{component_id}"
            result.devices[device] = {
                "name": attrs.get("DisplayName") or attrs.get("model") or f"Fronius {prefix}",
                "manufacturer": attrs.get("manufacturer", "Fronius"),
                "model": attrs.get("model"),
                "serial_number": attrs.get("serial"),
                "sw_version": attrs.get("sw_version") or attrs.get("this.rev-sw"),
                "hw_version": attrs.get("hw_version") or attrs.get("this.rev-hw"),
            }
            specs = METER_CHANNELS if endpoint == "meter" else BATTERY_CHANNELS
            for key, spec in specs.items():
                if key in channels:
                    name, unit, device_class, state_class, scale = spec
                    add(
                        device,
                        key,
                        name,
                        channels[key],
                        unit,
                        device_class,
                        state_class,
                        scale,
                        enabled=key != "BAT_ENERGYACTIVE_ESTIMATION_MAX_CAPACITY_F64",
                    )
            # Unknown channels stay available for inspection without guessed units.
            for key, value in channels.items():
                if key not in specs and (number(value) is not None or isinstance(value, str)):
                    add(device, key, key, value, state_class=None, diagnostic=True, enabled=False)
            if endpoint == "battery":
                capacity = decode_nameplate(attrs.get("nameplate")).get("capacity_wh")
                if number(capacity) is not None:
                    add(
                        device,
                        "capacity_wh",
                        "Nameplate capacity",
                        capacity,
                        "kWh",
                        "energy_storage",
                        scale=0.001,
                    )

    for status in payloads.get("devices", []):
        kind = status.get("type")
        candidates = [key for key in result.devices if key.endswith(f":{status.get('id')}")]
        if kind == "inverter":
            candidates = [key for key in result.devices if key.startswith("inverter:")]
        device = candidates[0] if len(candidates) == 1 else f"status:{status.get('id') or kind}"
        result.devices.setdefault(device, {"name": f"Fronius {kind}", "manufacturer": "Fronius"})
        add(
            device,
            "status",
            "Device status",
            status.get("statusMessage"),
            state_class=None,
            diagnostic=True,
        )
    return result


# Channel energies: meter Wh -> kWh; battery Ws -> kWh.
METER_CHANNELS = {
    "SMARTMETER_POWERACTIVE_MEAN_SUM_F64": ("Active power", "W", "power", "measurement", 1),
    "SMARTMETER_FREQUENCY_MEAN_F64": ("Frequency", "Hz", "frequency", "measurement", 1),
    "SMARTMETER_ENERGYACTIVE_CONSUMED_SUM_F64": (
        "Consumed energy total",
        "kWh",
        "energy",
        "total_increasing",
        0.001,
    ),
    "SMARTMETER_ENERGYACTIVE_PRODUCED_SUM_F64": (
        "Produced energy total",
        "kWh",
        "energy",
        "total_increasing",
        0.001,
    ),
}
for phase in range(1, 4):
    for channel, name, unit, device_class in (
        ("CURRENT", "Current", "A", "current"),
        ("VOLTAGE", "Voltage", "V", "voltage"),
        ("POWERACTIVE", "Active power", "W", "power"),
    ):
        METER_CHANNELS[f"SMARTMETER_{channel}_{phase:02}_F64"] = (
            f"{name} L{phase}",
            unit,
            device_class,
            "measurement",
            1,
        )

BATTERY_CHANNELS = {
    "BAT_VALUE_STATE_OF_CHARGE_RELATIVE_F32": ("State of charge", "%", "battery", "measurement", 1),
    "BAT_VALUE_STATE_OF_HEALTH_RELATIVE_U16": ("State of health", "%", None, "measurement", 1),
    "BAT_CURRENT_DC_F64": ("DC current", "A", "current", "measurement", 1),
    "BAT_VOLTAGE_DC_INTERNAL_F64": ("DC voltage", "V", "voltage", "measurement", 1),
    "BAT_TEMPERATURE_CELL_F64": ("Cell temperature", "°C", "temperature", "measurement", 1),
    "BAT_TEMPERATURE_CELL_MIN_F64": (
        "Minimum cell temperature",
        "°C",
        "temperature",
        "measurement",
        1,
    ),
    "BAT_TEMPERATURE_CELL_MAX_F64": (
        "Maximum cell temperature",
        "°C",
        "temperature",
        "measurement",
        1,
    ),
    "BAT_ENERGYACTIVE_MAX_CAPACITY_F64": (
        "Maximum capacity",
        "kWh",
        "energy_storage",
        "measurement",
        1 / 3_600_000,
    ),
    "BAT_ENERGYACTIVE_ESTIMATION_MAX_CAPACITY_F64": (
        "Estimated capacity",
        "kWh",
        "energy_storage",
        "measurement",
        1 / 3_600_000,
    ),
    "BAT_ENERGYACTIVE_LIFETIME_CHARGED_F64": (
        "Charge energy total",
        "kWh",
        "energy",
        "total_increasing",
        1 / 3_600_000,
    ),
    "BAT_ENERGYACTIVE_LIFETIME_DISCHARGED_F64": (
        "Discharge energy total",
        "kWh",
        "energy",
        "total_increasing",
        1 / 3_600_000,
    ),
}
