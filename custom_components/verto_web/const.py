"""Constants for the local Verto web integration."""

DOMAIN = "verto_web"
DEFAULT_INTERVAL = 10
ENDPOINTS = {
    "powerflow": "/api/status/powerflow",
    "devices": "/api/status/devices",
    "meter": "/api/components/PowerMeter/readable",
    "battery": "/api/components/BatteryManagementSystem/readable",
}
