"""DataUpdateCoordinator for the Habitica integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from io import BytesIO
import logging
from typing import Any

from aiohttp import ClientError
from habiticalib import (
    Avatar,
    ContentData,
    Habitica,
    HabiticaException,
    NotAuthorizedError,
    TaskData,
    TaskFilter,
    TooManyRequestsError,
    UserData,
)
from habiticalib.typedefs import GroupData

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    HomeAssistantError,
)
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class HabiticaRuntimeData:
    """Holds the coordinators."""

    me: HabiticaDataUpdateCoordinator
    party: HabiticaPartyCoordinator


@dataclass
class HabiticaData:
    """Habitica data."""

    user: UserData
    tasks: list[TaskData]


@dataclass
class HabiticaParty:
    """Habitica Party data."""

    party: GroupData
    members: list[UserData]


type HabiticaConfigEntry = ConfigEntry[HabiticaRuntimeData]


class HabiticaDataUpdateCoordinator(DataUpdateCoordinator[HabiticaData]):
    """Habitica Data Update Coordinator."""

    config_entry: HabiticaConfigEntry

    def __init__(
        self, hass: HomeAssistant, config_entry: HabiticaConfigEntry, habitica: Habitica
    ) -> None:
        """Initialize the Habitica data coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
            request_refresh_debouncer=Debouncer(
                hass,
                _LOGGER,
                cooldown=5,
                immediate=False,
            ),
        )
        self.habitica = habitica
        self.content: ContentData

    async def _async_setup(self) -> None:
        """Set up Habitica integration."""

        try:
            user = await self.habitica.get_user()
            self.content = (
                await self.habitica.get_content(user.data.preferences.language)
            ).data
        except NotAuthorizedError as e:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="authentication_failed",
            ) from e
        except TooManyRequestsError as e:
            raise ConfigEntryNotReady(
                translation_domain=DOMAIN,
                translation_key="setup_rate_limit_exception",
                translation_placeholders={"retry_after": str(e.retry_after)},
            ) from e
        except HabiticaException as e:
            raise ConfigEntryNotReady(
                translation_domain=DOMAIN,
                translation_key="service_call_exception",
                translation_placeholders={"reason": str(e.error.message)},
            ) from e
        except ClientError as e:
            raise ConfigEntryNotReady(
                translation_domain=DOMAIN,
                translation_key="service_call_exception",
                translation_placeholders={"reason": str(e)},
            ) from e

        if not self.config_entry.data.get(CONF_NAME):
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={**self.config_entry.data, CONF_NAME: user.data.profile.name},
            )

    async def _async_update_data(self) -> HabiticaData:
        try:
            user = (await self.habitica.get_user()).data
            tasks = (await self.habitica.get_tasks()).data
            completed_todos = (
                await self.habitica.get_tasks(TaskFilter.COMPLETED_TODOS)
            ).data
        except TooManyRequestsError:
            _LOGGER.debug("Rate limit exceeded, will try again later")
            return self.data
        except HabiticaException as e:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="service_call_exception",
                translation_placeholders={"reason": str(e.error.message)},
            ) from e
        except ClientError as e:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="service_call_exception",
                translation_placeholders={"reason": str(e)},
            ) from e
        else:
            return HabiticaData(user=user, tasks=tasks + completed_todos)

    async def execute(
        self, func: Callable[[HabiticaDataUpdateCoordinator], Any]
    ) -> None:
        """Execute an API call."""

        try:
            await func(self)
        except TooManyRequestsError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="setup_rate_limit_exception",
                translation_placeholders={"retry_after": str(e.retry_after)},
            ) from e
        except HabiticaException as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="service_call_exception",
                translation_placeholders={"reason": e.error.message},
            ) from e
        except ClientError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="service_call_exception",
                translation_placeholders={"reason": str(e)},
            ) from e
        else:
            await self.async_request_refresh()

    async def generate_avatar(self, avatar: Avatar) -> bytes:
        """Generate Avatar."""

        png = BytesIO()
        await self.habitica.generate_avatar(fp=png, avatar=avatar, fmt="PNG")

        return png.getvalue()


class HabiticaPartyCoordinator(DataUpdateCoordinator[HabiticaParty]):
    """Habitica Party Coordinator."""

    config_entry: HabiticaConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: HabiticaConfigEntry,
        habitica: Habitica,
    ) -> None:
        """Initialize the Habitica party coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=20),
        )
        self.habitica = habitica

    async def _async_update_data(self) -> HabiticaParty:
        """Fetch the latest party data."""

        try:
            party = (await self.habitica.get_group()).data
            members = (await self.habitica.get_group_members(public_fields=True)).data
        except TooManyRequestsError:
            _LOGGER.debug("Rate limit exceeded, will try again later")
            return self.data
        except HabiticaException as e:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="service_call_exception",
                translation_placeholders={"reason": str(e.error.message)},
            ) from e
        except ClientError as e:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="service_call_exception",
                translation_placeholders={"reason": str(e)},
            ) from e
        else:
            return HabiticaParty(party, members)
