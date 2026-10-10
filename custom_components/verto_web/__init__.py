"""Home Assistant support for the Fronius Verto internal web API."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import VertoClient
from .const import DEFAULT_INTERVAL
from .coordinator import VertoCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one inverter and its discovered components."""
    coordinator = VertoCoordinator(
        hass,
        entry,
        VertoClient(async_get_clientsession(hass), entry.data[CONF_HOST]),
        entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_INTERVAL),
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload platforms and polling listeners."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Apply changed polling options."""
    await hass.config_entries.async_reload(entry.entry_id)
