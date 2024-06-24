"""The ista Ecotrend integration."""

from __future__ import annotations

import logging

from pyecotrend_ista import KeycloakError, LoginError, PyEcotrendIsta, ServerError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .const import CONF_CODE, CONF_OTP, DOMAIN
from .coordinator import IstaCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

type IstaConfigEntry = ConfigEntry[IstaCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: IstaConfigEntry) -> bool:
    """Set up ista EcoTrend from a config entry."""
    totp: str | None = None
    if totp := entry.data.get(CONF_CODE):
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, CONF_CODE: ""},
        )
    elif otp_entity := entry.options.get(CONF_OTP):
        if state := hass.states.get(otp_entity):
            totp = state.state

    ista = PyEcotrendIsta(
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
        totp=totp,
    )

    try:
        await hass.async_add_executor_job(ista.login)
    except ServerError as e:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="connection_exception",
        ) from e
    except (LoginError, KeycloakError) as e:
        raise ConfigEntryAuthFailed(
            translation_domain=DOMAIN,
            translation_key="authentication_exception",
            translation_placeholders={CONF_EMAIL: entry.data[CONF_EMAIL]},
        ) from e

    coordinator = IstaCoordinator(hass, ista)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: IstaConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
