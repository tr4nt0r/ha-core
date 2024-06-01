"""The ista Ecotrend integration."""

from __future__ import annotations

import logging

from pyecotrend_ista.exception_classes import (
    InternalServerError,
    LoginError,
    ServerError,
)
from pyecotrend_ista.pyecotrend_ista import PyEcotrendIsta
from requests.exceptions import RequestException

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import IstaCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

type IstaConfigEntry = ConfigEntry[IstaCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: IstaConfigEntry) -> bool:
    """Set up ista Ecotrend from a config entry."""
    ista = PyEcotrendIsta(
        entry.data[CONF_EMAIL],
        entry.data[CONF_PASSWORD],
        _LOGGER,
    )
    try:
        await hass.async_add_executor_job(ista.login)
    except (ServerError, InternalServerError, RequestException, TimeoutError) as e:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="connection_exception",
        ) from e
    except LoginError as e:
        raise ConfigEntryAuthFailed(
            translation_domain=DOMAIN,
            translation_key="authentication_exception",
            translation_placeholders={CONF_EMAIL: entry.data[CONF_EMAIL]},
        ) from e

    entry.runtime_data = IstaCoordinator(hass, ista)
    await entry.runtime_data.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: IstaConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
