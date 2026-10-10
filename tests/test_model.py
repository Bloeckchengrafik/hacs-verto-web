"""Test real sign conventions, heterogeneous energy units and missing values."""

import copy

import pytest

from custom_components.verto_web.model import number, parse_snapshot


def test_powerflow_signs(payloads):
    readings = parse_snapshot(payloads, {}).readings
    assert readings["site", "P_Load"].value == pytest.approx(574.2786425)
    assert readings["site", "P_Grid_0"].value == 0
    assert readings["site", "P_Grid_1"].value == pytest.approx(7.60417)
    assert readings["site", "P_Akku_0"].value == pytest.approx(647.606018)
    assert readings["site", "P_Akku_1"].value == 0
    assert readings["site", "P_PV"].value == 0
    assert readings["site", "BackupMode"].value is False


def test_import_and_charging(payloads):
    payloads["powerflow"]["site"].update(P_Grid=400, P_Akku=-300)
    readings = parse_snapshot(payloads, {}).readings
    assert readings["site", "P_Grid_0"].value == 400
    assert readings["site", "P_Grid_1"].value == 0
    assert readings["site", "P_Akku_0"].value == 0
    assert readings["site", "P_Akku_1"].value == 300


def test_energy_units(payloads):
    readings = parse_snapshot(payloads, {}).readings
    assert readings["site", "E_Total"].value == pytest.approx(589.2705463888889)
    assert not readings["site", "E_Total"].enabled
    assert readings[
        "meter:meter-example", "SMARTMETER_ENERGYACTIVE_CONSUMED_SUM_F64"
    ].value == pytest.approx(1153.972)
    assert readings[
        "meter:meter-example", "SMARTMETER_ENERGYACTIVE_PRODUCED_SUM_F64"
    ].value == pytest.approx(9256.715)
    assert readings[
        "battery:battery-example", "BAT_ENERGYACTIVE_LIFETIME_CHARGED_F64"
    ].value == pytest.approx(218.935)
    assert readings[
        "battery:battery-example", "BAT_ENERGYACTIVE_LIFETIME_DISCHARGED_F64"
    ].value == pytest.approx(201.926)
    assert readings[
        "battery:battery-example", "BAT_ENERGYACTIVE_MAX_CAPACITY_F64"
    ].value == pytest.approx(9.369)
    assert readings["battery:battery-example", "capacity_wh"].value == pytest.approx(9.477)


def test_missing_data_does_not_become_zero(payloads):
    payloads["powerflow"]["site"]["P_Grid"] = None
    payloads.pop("battery")
    snapshot = parse_snapshot(payloads, {"battery": "VertoError"})
    assert snapshot.readings["site", "P_Grid_0"].value is None
    assert snapshot.readings["site", "P_Grid_1"].value is None
    assert not any(key[0].startswith("battery:") for key in snapshot.readings)
    assert snapshot.errors == {"battery": "VertoError"}


def test_unknown_channels_and_distinct_meters(payloads):
    components = payloads["meter"]["Body"]["Data"]
    components["secondary"] = copy.deepcopy(components["meter-example"])
    snapshot = parse_snapshot(payloads, {})
    raw = snapshot.readings["meter:meter-example", "FUTURE_UNKNOWN_CHANNEL"]
    assert raw.value == 42
    assert raw.unit is None and raw.state_class is None
    assert not raw.enabled and raw.diagnostic
    assert ("meter:secondary", "SMARTMETER_VOLTAGE_01_F64") in snapshot.readings
    assert snapshot.readings["battery:battery-example", "status"].value == "STATE_3"


@pytest.mark.parametrize("value", [None, True, "123", float("nan"), float("inf")])
def test_invalid_numeric_values(value):
    assert number(value) is None
