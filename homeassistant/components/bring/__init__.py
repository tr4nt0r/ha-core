"""The Bring! integration."""
from __future__ import annotations

from enum import StrEnum
import logging
from typing import Final

from python_bring_api.bring import Bring
from python_bring_api.exceptions import (
    BringAuthException,
    BringParseException,
    BringRequestException,
)
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import bind_hass

from .const import DOMAIN
from .coordinator import BringDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.TODO]

ATTR_SENDER: Final = "sender"
ATTR_ITEM_NAME: Final = "item_name"
ATTR_NOTIFICATION_TYPE: Final = "notification_type"
ATTR_LIST: Final = "bring_list"


class NOTIFICATION_TYPE(StrEnum):
    """Bring Notification type.

    GOING_SHOPPING: "I'm going shopping! - Last chance for adjustments"
    CHANGED_LIST: "List changed - Check it out"
    SHOPPING_DONE: "Shopping done - you can relax"
    URGENT_MESSAGE: "Breaking news - Please get {itemName}!

    TODO: remove and import from python-bring-api types when PR merged
    """

    GOING_SHOPPING = "GOING_SHOPPING"
    CHANGED_LIST = "CHANGED_LIST"
    SHOPPING_DONE = "SHOPPING_DONE"
    URGENT_MESSAGE = "URGENT_MESSAGE"


_LOGGER = logging.getLogger(__name__)


@callback
@bind_hass
def async_notify(
    hass: HomeAssistant,
    entity_id: str,
    notification_type: NOTIFICATION_TYPE,
    item_name: str | None = None,
) -> None:
    """Generate a notification."""


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Bring! component."""

    @callback
    def notify_service(call: ServiceCall) -> None:
        """Handle a notification service call."""
        async_notify(
            hass,
            call.data[ATTR_LIST],
            call.data[ATTR_NOTIFICATION_TYPE],
            call.data.get(ATTR_ITEM_NAME),
        )

    hass.services.async_register(
        DOMAIN,
        "notify",
        notify_service,
        vol.Schema(
            {
                vol.Required(ATTR_LIST): cv.entities_domain(DOMAIN),
                vol.Required(
                    ATTR_NOTIFICATION_TYPE, default=NOTIFICATION_TYPE.GOING_SHOPPING
                ): vol.In(NOTIFICATION_TYPE),
                vol.Optional(ATTR_ITEM_NAME): cv.string,
            }
        ),
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Bring! from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]

    bring = Bring(email, password)

    try:
        await hass.async_add_executor_job(bring.login)
        await hass.async_add_executor_job(bring.loadLists)
    except BringRequestException as e:
        raise ConfigEntryNotReady(
            f"Timeout while connecting for email '{email}'"
        ) from e
    except BringAuthException as e:
        _LOGGER.error(
            "Authentication failed for '%s', check your email and password",
            email,
        )
        raise ConfigEntryError(
            f"Authentication failed for '{email}', check your email and password"
        ) from e
    except BringParseException as e:
        _LOGGER.error(
            "Failed to parse request '%s', check your email and password",
            email,
        )
        raise ConfigEntryError(
            f"Failed to parse request '{email}', check your email and password"
        ) from e

    coordinator = BringDataUpdateCoordinator(hass, bring)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
