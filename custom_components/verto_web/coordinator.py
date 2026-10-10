"""Shared polling for all Verto entities."""

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import VertoClient, VertoError
from .const import DOMAIN
from .model import Snapshot, parse_snapshot

_LOGGER = logging.getLogger(__name__)


class VertoCoordinator(DataUpdateCoordinator[Snapshot]):
    """Fetch every endpoint once per update, regardless of entity count."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: VertoClient, interval: int
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )
        self.client = client

    async def _async_update_data(self) -> Snapshot:
        try:
            payloads, errors = await self.client.snapshot()
            return parse_snapshot(payloads, errors)
        except VertoError as err:
            raise UpdateFailed(str(err)) from err
