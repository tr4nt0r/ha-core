"""Bring! platform for notify component."""
from __future__ import annotations

import logging

from python_bring_api.bring import Bring
import voluptuous as vol

from homeassistant.components.notify import BaseNotificationService
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


# def get_service(
#     hass: HomeAssistant,
#     config: ConfigType,
#     discovery_info: DiscoveryInfoType | None = None,
# ) -> BringNotificationService:
#     """Get the Bring! notification service."""
#     return BringNotificationService(
#         hass,
#         config[CONF_EMAIL],
#         config[CONF_PASSWORD],
#     )

EVENT_NOTIFY = "notify"


def get_service(
    hass: HomeAssistant,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> BringNotificationService:
    """Get the demo notification service."""
    return BringNotificationService(hass)


class BringNotificationService(BaseNotificationService):
    """Implement demo notification service."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the service."""
        self.hass = hass

    @property
    def targets(self) -> dict[str, str]:
        """Return a dictionary of registered targets."""
        return {"Bring! Einkaufsliste (Username)": "listuuid"}

    def send_message(self, message: str = "", **kwargs: Any) -> None:
        """Send a message to a user."""
