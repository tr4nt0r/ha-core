"""The Playstation Network integration."""

from __future__ import annotations

from dataclasses import dataclass

from psnawp_api.core.psnawp_exceptions import PSNAWPAuthenticationError
from psnawp_api.psnawp import PSNAWP

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .const import DOMAIN, PLAYSTATION_NETWORK_API, PLAYSTATION_NETWORK_COORDINATOR
from .coordinator import PlaystationNetworkCoordinator

PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER]


@dataclass
class RuntimeData:
    """Playstation Network Runtime Data."""

    coordinator: PlaystationNetworkCoordinator


type PlaystationNetworkConfigEntry = ConfigEntry[RuntimeData]


async def async_setup_entry(
    hass: HomeAssistant, entry: PlaystationNetworkConfigEntry
) -> bool:
    """Set up Playstation Network from a config entry."""

    try:
        npsso: str = str(entry.data.get("npsso"))
        psn = PSNAWP(npsso)
    except PSNAWPAuthenticationError as error:
        raise ConfigEntryAuthFailed(error) from error
    except Exception as ex:
        raise ConfigEntryNotReady(ex) from ex

    try:
        user = await hass.async_add_executor_job(lambda: psn.user(online_id="me"))
        client = psn.me()
        coordinator = PlaystationNetworkCoordinator(hass, psn, user, client)
    except PSNAWPAuthenticationError as error:
        raise ConfigEntryAuthFailed(error) from error
    except Exception as ex:
        raise ConfigEntryNotReady(ex) from ex

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        PLAYSTATION_NETWORK_COORDINATOR: coordinator,
        PLAYSTATION_NETWORK_API: psn,
    }

    entry.runtime_data = RuntimeData(coordinator=coordinator)

    if entry.unique_id is None:
        hass.config_entries.async_update_entry(entry, unique_id=user.online_id)
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))
    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Update Listener."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: PlaystationNetworkConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
