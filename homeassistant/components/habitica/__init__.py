"""The habitica integration."""

from aiohttp import ClientError
from habiticalib import (
    Habitica,
    HabiticaException,
    NotAuthorizedError,
    TooManyRequestsError,
)
from habitipy.aio import HabitipyAsync

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_API_KEY,
    CONF_NAME,
    CONF_URL,
    CONF_VERIFY_SSL,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .const import CONF_API_USER, DOMAIN, X_CLIENT
from .coordinator import HabiticaDataUpdateCoordinator
from .services import async_setup_services
from .types import HabiticaConfigEntry

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CALENDAR,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TODO,
]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Habitica service."""

    async_setup_services(hass)
    return True


async def async_setup_entry(
    hass: HomeAssistant, config_entry: HabiticaConfigEntry
) -> bool:
    """Set up habitica from a config entry."""

    class HAHabitipyAsync(HabitipyAsync):
        """Closure API class to hold session."""

        def __call__(self, **kwargs):
            return super().__call__(websession, **kwargs)

        def _make_headers(self) -> dict[str, str]:
            headers = super()._make_headers()
            headers.update({"x-client": X_CLIENT})
            return headers

    websession = async_get_clientsession(
        hass, verify_ssl=config_entry.data.get(CONF_VERIFY_SSL, True)
    )

    api = await hass.async_add_executor_job(
        HAHabitipyAsync,
        {
            "url": config_entry.data[CONF_URL],
            "login": config_entry.data[CONF_API_USER],
            "password": config_entry.data[CONF_API_KEY],
        },
    )

    async with Habitica(
        session=websession,
        api_user=config_entry.data[CONF_API_USER],
        api_key=config_entry.data[CONF_API_KEY],
        url=config_entry.data[CONF_URL],
        x_client=X_CLIENT,
    ) as habitica:
        try:
            user = await habitica.get_user("profile")
        except TooManyRequestsError as e:
            raise ConfigEntryNotReady(
                translation_domain=DOMAIN,
                translation_key="setup_rate_limit_exception",
                translation_placeholders={
                    "retry_after": f"{round(e.retry_after or 0)}"
                },
            ) from e
        except NotAuthorizedError as e:
            raise ConfigEntryNotReady(
                translation_domain=DOMAIN,
                translation_key="authentication_error",
            ) from e
        except (ClientError, HabiticaException) as e:
            raise ConfigEntryNotReady(e) from e

        if not config_entry.data.get(CONF_NAME):
            name = user.data.profile.name
            hass.config_entries.async_update_entry(
                config_entry,
                data={**config_entry.data, CONF_NAME: name},
            )

        coordinator = HabiticaDataUpdateCoordinator(hass, api, habitica)

    await coordinator.async_config_entry_first_refresh()

    config_entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
