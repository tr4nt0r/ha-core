"""The Pinecil integration."""

from __future__ import annotations

import logging

from pinecil import BLE, Pinecil

from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import PinecilCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Pinecil from a config entry."""
    _LOGGER.debug("Setting up entry from config %s", entry)
    assert entry.unique_id

    ble_device = async_ble_device_from_address(hass, entry.unique_id, True)
    if not ble_device:
        _LOGGER.debug("Device not found %s", entry.title)
        raise ConfigEntryNotReady(f"Could not find device {entry.title}")

    pinecil = Pinecil(BLE(entry.unique_id))

    coordinator = PinecilCoordinator(hass, pinecil, ble_device, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
