"""Update coordinator for Pinecil Integration."""

from datetime import timedelta
import logging

from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from pinecil import DeviceDisconnectedException, DeviceNotFoundException, Pinecil

# from homeassistant.components.bluetooth.api import async_address_present
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, MANUFACTURER, MODEL

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=5)


class PinecilCoordinator(DataUpdateCoordinator):
    """Pinecil coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        pinecil: Pinecil,
        ble_device: BLEDevice,
        entry: ConfigEntry,
    ) -> None:
        """Initialize Pinecil coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.pinecil = pinecil
        self.ble_device = ble_device
        assert entry.unique_id
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            connections={(CONNECTION_BLUETOOTH, entry.unique_id)},
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    async def _async_update_data(self):
        """Fetch data from Pinecil."""

        try:
            if "sw_version" not in self.device_info:
                info = await self.pinecil.get_info()
                self.device_info.update(
                    DeviceInfo(
                        name=info["name"],
                        sw_version=info["build"],
                        serial_number=info["id"],
                    )
                )
                _LOGGER.debug("Retrieved device info from pinecil %s", info)
                # settings = await self.pinecil.get_all_settings()
                # _LOGGER.debug("Retrieved settings from pinecil %s", settings)

            data = await self.pinecil.get_live_data()
            _LOGGER.debug("Retrieved live data from pinecil %s", data)

        except (BleakError, DeviceDisconnectedException, DeviceNotFoundException) as e:
            _LOGGER.debug("Device not reachable")
            raise UpdateFailed(e) from e
        else:
            return data
