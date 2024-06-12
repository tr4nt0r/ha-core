"""The Pinecil integration."""

from __future__ import annotations

from pynecil import CommunicationError, Pynecil

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import PinecilCoordinator

PLATFORMS: list[Platform] = [Platform.NUMBER, Platform.SENSOR]

type PinecilConfigEntry = ConfigEntry[PinecilCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: PinecilConfigEntry) -> bool:
    """Set up Pinecil from a config entry."""

    ble_device = bluetooth.async_ble_device_from_address(
        hass, entry.data[CONF_ADDRESS], connectable=True
    )
    if not ble_device:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="setup_device_unavailable_exception",
            translation_placeholders={CONF_ADDRESS: entry.data[CONF_ADDRESS]},
        )

    pinecil = Pynecil(ble_device)
    try:
        device = await pinecil.get_device_info()
    except CommunicationError as e:
        await pinecil.disconnect()
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="setup_device_unavailable_exception",
            translation_placeholders={CONF_ADDRESS: entry.data[CONF_ADDRESS]},
        ) from e

    device_info = DeviceInfo(
        identifiers={(DOMAIN, entry.data[CONF_ADDRESS])},
        connections={(CONNECTION_BLUETOOTH, entry.data[CONF_ADDRESS])},
        manufacturer=MANUFACTURER,
        model=MODEL,
        name="Pinecil",
        sw_version=device.build,
        serial_number=device.device_sn,
    )

    coordinator = PinecilCoordinator(hass, pinecil, device_info)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: PinecilConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
