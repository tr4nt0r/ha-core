"""Update coordinator for Pinecil Integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import TYPE_CHECKING

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth.active_update_coordinator import (
    ActiveBluetoothDataUpdateCoordinator,
)
from homeassistant.core import CoreState, HomeAssistant, callback
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo

from .const import DOMAIN, MANUFACTURER, MODEL
from .pinecil import Pinecil

if TYPE_CHECKING:
    from bleak.backends.device import BLEDevice

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=5)


# class PinecilCoordinator(DataUpdateCoordinator):
#     """Pinecil coordinator."""

#     def __init__(
#         self,
#         hass: HomeAssistant,
#         pinecil: Pinecil,
#         ble_device: BLEDevice,
#         entry: ConfigEntry,
#     ) -> None:
#         """Initialize Pinecil coordinator."""
#         super().__init__(
#             hass,
#             _LOGGER,
#             name=DOMAIN,
#             update_interval=SCAN_INTERVAL,
#         )
#         self.pinecil = pinecil
#         self.ble_device = ble_device
#         assert entry.unique_id
#         self.device_info = DeviceInfo(
#             identifiers={(DOMAIN, entry.unique_id)},
#             connections={(CONNECTION_BLUETOOTH, entry.unique_id)},
#             manufacturer=MANUFACTURER,
#             model=MODEL,
#         )

#     async def _async_update_data(self):
#         """Fetch data from Pinecil."""

#         try:
#             if "sw_version" not in self.device_info:
#                 info = await self.pinecil.get_info()
#                 self.device_info.update(
#                     DeviceInfo(
#                         name=info["name"],
#                         sw_version=info["build"],
#                         serial_number=info["id"],
#                     )
#                 )
#                 _LOGGER.debug("Retrieved device info from pinecil %s", info)
#                 # settings = await self.pinecil.get_all_settings()
#                 # _LOGGER.debug("Retrieved settings from pinecil %s", settings)

#             data = await self.pinecil.get_live_data()
#             _LOGGER.debug("Retrieved live data from pinecil %s", data)

#         except (BleakError, DeviceDisconnectedException, DeviceNotFoundException) as e:
#             _LOGGER.debug("Device not reachable")
#             raise UpdateFailed(e) from e
#         else:
#             return data


class PinecilActiveBluetoothDataUpdateCoordinator(
    ActiveBluetoothDataUpdateCoordinator[None]
):
    """Class to manage fetching example data."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        ble_device: BLEDevice,
        device: Pinecil,
    ) -> None:
        """Initialize example data coordinator."""
        super().__init__(
            hass=hass,
            logger=logger,
            address=ble_device.address,
            needs_poll_method=self._needs_poll,
            poll_method=self._async_update,
            mode=bluetooth.BluetoothScanningMode.ACTIVE,
            connectable=True,
        )
        self.ble_device = ble_device
        self.device = device
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, ble_device.address)},
            connections={(CONNECTION_BLUETOOTH, ble_device.address)},
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @callback
    def _needs_poll(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        seconds_since_last_poll: float | None,
    ) -> bool:
        # Only poll if hass is running, we need to poll,
        # and we actually have a way to connect to the device
        _LOGGER.debug("_needs poll")
        return True
        return (
            self.hass.state == CoreState.running
            and self.device.poll_needed(seconds_since_last_poll)
            and bool(
                bluetooth.async_ble_device_from_address(
                    self.hass, service_info.device.address, connectable=True
                )
            )
        )

    async def _async_update(
        self, service_info: bluetooth.BluetoothServiceInfoBleak
    ) -> None:
        """Poll the device."""
        _LOGGER.debug("Device polling request received")

        service_info = await bluetooth.async_process_advertisements(
            self.hass,
            self.needs_poll,
            {"address": service_info.address, "connectable": True},
            bluetooth.BluetoothScanningMode.ACTIVE,
            1,
        )

    @callback
    def _async_handle_unavailable(
        self, service_info: bluetooth.BluetoothServiceInfoBleak
    ) -> None:
        """Handle the device going unavailable."""
        _LOGGER.debug("Device went unvavailable")
        super()._async_handle_unavailable(service_info)

    @callback
    def _async_handle_bluetooth_event(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        """Handle a Bluetooth event."""
        # Your device should process incoming advertisement data
        _LOGGER.debug("Advertisement received %s", change)

        # super()._async_handle_bluetooth_event(service_info, change)
