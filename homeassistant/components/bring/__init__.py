"""The Bring! integration."""
from __future__ import annotations

import logging

from python_bring_api.bring import Bring
from python_bring_api.exceptions import (
    BringAuthException,
    BringParseException,
    BringRequestException,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import BringDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.TODO]

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Bring! component."""

    hass.async_create_task(
        async_load_platform(hass, Platform.NOTIFY, DOMAIN, {}, config)
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
