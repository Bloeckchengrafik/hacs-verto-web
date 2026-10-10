"""Sanitized fixtures with values from the supplied Verto responses."""

import pytest


@pytest.fixture
def payloads():
    return {
        "powerflow": {
            "site": {
                "P_Grid": -7.60417,
                "P_Load": -574.2786425,
                "P_Akku": 647.606018,
                "P_PV": 0.0,
                "E_Total": 589270.5463888889,
                "E_Day": None,
                "BackupMode": False,
                "BatteryStandby": True,
            },
            "inverters": [{"ID": 1, "P": 578.327209, "SOC": 36.099998}],
        },
        "devices": [
            {"type": "inverter", "status": 1, "statusMessage": "STATE_RUNNING"},
            {
                "type": "powermeter",
                "id": "meter-example",
                "status": 1,
                "statusMessage": "STATE_RUNNING",
            },
            {"type": "battery", "id": "battery-example", "status": 1, "statusMessage": "STATE_3"},
        ],
        "battery": {
            "Body": {
                "Data": {
                    "battery-example": {
                        "attributes": {
                            "model": "Reserva",
                            "serial": "EXAMPLE",
                            "nameplate": '{"capacity_wh":9477}',
                        },
                        "channels": {
                            "BAT_VALUE_STATE_OF_CHARGE_RELATIVE_F32": 36.099998474121094,
                            "BAT_ENERGYACTIVE_LIFETIME_CHARGED_F64": 788166000.0,
                            "BAT_ENERGYACTIVE_LIFETIME_DISCHARGED_F64": 726933600.0,
                            "BAT_ENERGYACTIVE_MAX_CAPACITY_F64": 33728400.0,
                            "BAT_TEMPERATURE_CELL_F64": 24.05,
                            "BAT_CURRENT_DC_F64": -1.89792663476874,
                            "BAT_MODE_STATUS_BMS_U32": 2.0,
                        },
                    }
                }
            },
            "Head": {"Status": {"Code": 0}},
        },
        "meter": {
            "Body": {
                "Data": {
                    "meter-example": {
                        "attributes": {"model": "Smart Meter IP 5kA-3", "meter-location": "0"},
                        "channels": {
                            "SMARTMETER_POWERACTIVE_MEAN_SUM_F64": -7.60417,
                            "SMARTMETER_ENERGYACTIVE_CONSUMED_SUM_F64": 1153972.0,
                            "SMARTMETER_ENERGYACTIVE_PRODUCED_SUM_F64": 9256715.0,
                            "SMARTMETER_VOLTAGE_01_F64": 231.6,
                            "SMARTMETER_CURRENT_01_F64": 0.544,
                            "SMARTMETER_POWERACTIVE_01_F64": 100.7,
                            "FUTURE_UNKNOWN_CHANNEL": 42.0,
                        },
                    }
                }
            },
            "Head": {"Status": {"Code": 0}},
        },
    }
