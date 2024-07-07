"""DataUpdateCoordinator for the Habitica integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from aiohttp import ClientResponseError
from habitipy.aio import HabitipyAsync

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import ADDITIONAL_USER_FIELDS, DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class HabiticaData:
    """Coordinator data class."""

    user: dict[str, Any]
    tasks: list[dict]


class HabiticaDataUpdateCoordinator(DataUpdateCoordinator[HabiticaData]):
    """Habitica Data Update Coordinator."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, habitipy: HabitipyAsync) -> None:
        """Initialize the Habitica data coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.api = habitipy

    async def _async_update_data(self) -> HabiticaData:
        user_fields = set(self.async_contexts()) | ADDITIONAL_USER_FIELDS

        try:
            user_response = await self.api.user.get()
            tasks_response = await self.api.tasks.user.get()
            tasks_response.extend(await self.api.tasks.user.get(type="completedTodos"))
        except ClientResponseError as error:
            raise UpdateFailed(f"Error communicating with API: {error}") from error

        return HabiticaData(user=user_response, tasks=tasks_response)
