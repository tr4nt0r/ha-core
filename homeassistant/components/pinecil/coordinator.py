"""Update coordinator for Pinecil Integration."""

from datetime import timedelta
import logging

from pinecil import Pinecil

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=5)


class PinecilCoordinator(DataUpdateCoordinator):
    """Pinecil coordinator."""

    def __init__(self, hass: HomeAssistant, pinecil: Pinecil) -> None:
        """Initialize Pinecil coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.pinecil = pinecil

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        return {}
