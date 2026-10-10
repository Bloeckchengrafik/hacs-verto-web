"""Diagnostics without addresses, serial numbers or raw device attributes."""


async def async_get_config_entry_diagnostics(hass, entry):
    coordinator = entry.runtime_data
    return {
        "last_update_success": coordinator.last_update_success,
        "endpoint_errors": coordinator.data.errors,
        "devices": [
            {
                "model": info.get("model"),
                "channels": [
                    reading.key
                    for reading in coordinator.data.readings.values()
                    if reading.device == device
                ],
            }
            for device, info in coordinator.data.devices.items()
        ],
    }
