"""LedSC light."""

import logging
from typing import Any

from websc_client import WebSCAsync, WebSClientAsync as WebSClient

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .consts import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities: AddEntitiesCallback
):
    """Connect to WebSC.

    load the configured devices from WebSC Server and add them to hass.
    """
    client = WebSClient(host=config.data[CONF_HOST], port=config.data[CONF_PORT])
    await client.connect()
    hass.async_create_background_task(client.observer(), name="ledsc-observer")

    devices: list[LedSCLightEntity] = []
    for websc in client.devices.values():
        ledsc = LedSCLightEntity(
            client_id=config.entry_id,
            websc=websc,
            hass=hass,
        )
        websc.set_callback(__generate_callback(ledsc))
        devices.append(ledsc)
    add_entities(devices, True)


class LedSCLightEntity(LightEntity):
    """Representation of an LedSC Light."""

    _attr_has_entity_name = True
    _attr_translation_key: str = "light"

    def __init__(
        self,
        client_id: str,
        websc: WebSCAsync,
        hass: HomeAssistant,
    ) -> None:
        """Initialize an LedSC Light."""
        self._hass: HomeAssistant = hass
        self._websc: WebSCAsync = websc
        self._attr_unique_id = f"{client_id}-{websc.name}"
        _LOGGER.debug("LedSC %s initialized!", websc.name)
        self._attr_device_info = DeviceInfo(
            manufacturer="LedSC",
            model="LedSC",
            name=websc.name,
            identifiers={(DOMAIN, f"{client_id}-{websc.name}")},
        )

    @property
    def supported_color_modes(self) -> set[ColorMode] | set[str] | None:
        """List of supported color modes."""
        return {ColorMode.RGBW}

    @property
    def color_mode(self) -> ColorMode | str | None:
        """Return the current color mode (static)."""
        return ColorMode.RGBW

    @property
    def available(self) -> bool:
        """Check if light is available."""
        return not self._websc.is_lost

    @property
    def brightness(self) -> int | None:
        """Return the brightness of the light."""
        return max(self._websc.rgbw)

    @brightness.setter
    def brightness(self, value: int) -> None:
        """Set brightness of the light."""
        actual = self.brightness
        if actual is None or actual == 0:
            self.hass.async_create_task(
                self._websc.set_rgbw(red=value, green=value, blue=value, white=value)
            )
        else:
            diff = value - actual
            ratio = diff / actual
            self.hass.async_create_task(
                self._websc.set_rgbw(
                    red=round(self._websc.red * (1 + ratio)),
                    green=round(self._websc.green * (1 + ratio)),
                    blue=round(self._websc.blue * (1 + ratio)),
                    white=round(self._websc.white * (1 + ratio)),
                )
            )

    @property
    def rgbw_color(self) -> tuple[int, int, int, int] | None:
        """Get color."""
        return self._websc.rgbw

    @rgbw_color.setter
    def rgbw_color(self, value: tuple[int, int, int, int]) -> None:
        """Set color to WebSC."""
        self.hass.async_create_task(
            self._websc.set_rgbw(
                red=value[0],
                green=value[1],
                blue=value[2],
                white=value[3],
            )
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        return bool(
            self._websc.red
            or self._websc.green
            or self._websc.blue
            or self._websc.white
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Instruct the light to turn on."""
        if "brightness" in kwargs:
            self.brightness = kwargs["brightness"]
        elif "rgbw_color" in kwargs:
            self.rgbw_color = kwargs["rgbw_color"]
        elif not self.is_on:
            await self.switch()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        if self.is_on:
            await self.switch()

    async def switch(self) -> None:
        """Send switch event to WebSC."""
        await self._websc.do_px_trigger()


def __generate_callback(ledsc: LedSCLightEntity):
    """Generates a callback to respond to a LedSC state change."""

    async def on_device_change(data: dict[str, int]):
        await ledsc.async_update_ha_state(force_refresh=True)

    return on_device_change
