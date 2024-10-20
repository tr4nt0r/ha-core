"""DataUpdateCoordinator for the Habitica integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from aiohttp import ClientError
from habiticalib import Habitica, HabiticaException, TaskFilter, TooManyRequestsError
from habiticalib.types import TaskData, UserData
from habitipy.aio import HabitipyAsync

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class HabiticaData:
    """Coordinator data class."""

    user: UserData
    tasks: list[TaskData]


class HabiticaDataUpdateCoordinator(DataUpdateCoordinator[HabiticaData]):
    """Habitica Data Update Coordinator."""

    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, habitipy: HabitipyAsync, habitica: Habitica
    ) -> None:
        """Initialize the Habitica data coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
            request_refresh_debouncer=Debouncer(
                hass,
                _LOGGER,
                cooldown=5,
                immediate=False,
            ),
        )
        self.api = habitipy
        self.habitica = habitica

    async def _async_update_data(self) -> HabiticaData:
        try:
            user = await self.habitica.get_user()
            task = await self.habitica.get_tasks()
            task_completed = await self.habitica.get_tasks(TaskFilter.COMPLETED_TODOS)
        except TooManyRequestsError:
            _LOGGER.debug("Rate limit exceeded, will try again later")
            return self.data
        except HabiticaException as e:
            raise UpdateFailed(
                f"Unable to connect to Habitica {e.error.message}"
            ) from e
        except ClientError as e:
            raise UpdateFailed(f"Error fetching Habitica data: {e.args[0]}") from e

        return HabiticaData(user=user.data, tasks=[*task.data, *task_completed.data])

    async def execute(
        self, func: Callable[[HabiticaDataUpdateCoordinator], Any]
    ) -> None:
        """Execute an API call."""

        try:
            await func(self)
        except TooManyRequestsError as e:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="setup_rate_limit_exception",
                translation_placeholders={
                    "retry_after": f"{round(e.retry_after or 0)}"
                },
            ) from e
        except (ClientError, HabiticaException) as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="service_call_exception",
            ) from e
        else:
            await self.async_request_refresh()
