"""Coordinator for the PlayStation Network Integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from psnawp_api.core.psnawp_exceptions import (
    PSNAWPAuthenticationError,
    PSNAWPServerError,
)

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .helpers import PlaystationNetwork, PlaystationNetworkData

_LOGGER = logging.getLogger(__name__)

type PlaystationNetworkConfigEntry = ConfigEntry[PlaystationNetworkCoordinator]

SCAN_INTERVAL = timedelta(seconds=30)
SCAN_INTERVAL_TROPHIES = timedelta(minutes=15)


class PlaystationNetworkBaseCoordinator[_DataT](DataUpdateCoordinator[_DataT]):
    """Base coordinator."""

    config_entry: PlaystationNetworkConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        psn: PlaystationNetwork,
        config_entry: PlaystationNetworkConfigEntry,
        update_interval: timedelta,
    ) -> None:
        """Initialize the Coordinator."""
        super().__init__(
            hass,
            name=DOMAIN,
            logger=_LOGGER,
            config_entry=config_entry,
            update_interval=update_interval,
        )

        self.psn = psn


class PlaystationNetworkCoordinator(PlaystationNetworkBaseCoordinator):
    """Data update coordinator for PSN."""

    def __init__(
        self,
        hass: HomeAssistant,
        psn: PlaystationNetwork,
        config_entry: PlaystationNetworkConfigEntry,
    ) -> None:
        """Initialize the Coordinator."""
        super().__init__(hass, psn, config_entry, SCAN_INTERVAL)

    async def _async_setup(self) -> None:
        """Set up the coordinator."""

        try:
            await self.psn.get_user()
        except PSNAWPAuthenticationError as error:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="not_ready",
            ) from error

    async def _async_update_data(self) -> PlaystationNetworkData:
        """Get the latest data from the PSN."""

        try:
            return await self.psn.get_data()
        except PSNAWPAuthenticationError as error:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="not_ready",
            ) from error
        except PSNAWPServerError as error:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
            ) from error


class PlaystationNetworkTrophyCoordinator(PlaystationNetworkBaseCoordinator):
    """Data update coordinator for trophy data."""

    def __init__(
        self,
        hass: HomeAssistant,
        psn: PlaystationNetwork,
        config_entry: PlaystationNetworkConfigEntry,
        subentry: ConfigSubentry,
    ) -> None:
        """Initialize the Coordinator."""
        super().__init__(hass, psn, config_entry, SCAN_INTERVAL_TROPHIES)

    async def _async_update_data(self) -> PlaystationNetworkData:
        """Get the latest data from the PSN."""

        try:
            return await self.psn.get_data()
        except PSNAWPAuthenticationError as error:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="not_ready",
            ) from error
        except PSNAWPServerError as error:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
            ) from error
