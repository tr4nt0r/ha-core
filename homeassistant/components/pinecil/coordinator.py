"""Update coordinator for Pinecil Integration."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

from pynecil import (
    CharSetting,
    CommunicationError,
    DeviceInfoResponse,
    LiveDataResponse,
    Pynecil,
    SettingsDataResponse,
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=5)
MIN_TIME_BETWEEN_SETTINGS_UPDATES = timedelta(seconds=60)


class PinecilCoordinator(DataUpdateCoordinator[LiveDataResponse]):
    """Pinecil coordinator."""

    _save_delayed_task: asyncio.Task | None = None
    settings: SettingsDataResponse = SettingsDataResponse()
    device: DeviceInfoResponse | None = None

    def __init__(self, hass: HomeAssistant, pinecil: Pynecil) -> None:
        """Initialize Pinecil coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.pinecil = pinecil
        self.hass = hass

    async def _async_update_data(self) -> LiveDataResponse:
        """Fetch data from Pinecil."""

        try:
            if not self.device:
                self.device = await self.pinecil.get_device_info()
            await self.update_settings()

            return await self.pinecil.get_live_data()

        except CommunicationError as e:
            await self.pinecil.disconnect()
            raise UpdateFailed("Cannot connect to device") from e

    async def update_settings(self) -> None:
        """Fetch settings from Pinecil."""

        if settings := set(self.async_contexts()):
            self.settings = await self.pinecil.get_settings(list(settings))

    async def save_settings(self) -> None:
        """Save settings to flash."""

        async def save_delayed():
            """Delay writing to flash.

            Prevent writing to flash for every write request to a setting,
            instead delay execution till user finished doing changes.
            This is done to reduce write cycles to the internal flash.
            """
            await asyncio.sleep(20)

            await self.pinecil.write(CharSetting.SETTINGS_SAVE, 1)
            _LOGGER.debug("Writing settings to flash")

        if not self._save_delayed_task or self._save_delayed_task.done():
            self._save_delayed_task = await self.hass.async_create_task(save_delayed())
