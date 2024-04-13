"""Notify platform for the Bring! integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from bring_api.exceptions import BringRequestException
from bring_api.types import BringNotificationType
import voluptuous as vol

from homeassistant.components.notify import NotifyEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.config_validation import make_entity_service_schema
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN
from .const import ATTR_ITEM_NAME, ATTR_NOTIFICATION_TYPE, MANUFACTURER, SERVICE_NAME
from .coordinator import BringData, BringDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Bring notify entity platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        BringNotify(coordinator, bring_list=bring_list, entry=config_entry)
        for bring_list in coordinator.data.values()
    )

    # registers service bring.send_message with custom service schema.
    # message is defined as radio input with predefined values, as bring only
    # accepts 4 predefined values GOING_SHOPPING, CHANGED_LIST, SHOPPING_DONE, URGENT_MESSAGE.
    # These are like translation_keys and get localized in the app to notification in the users language.
    # URGENT_MESSAGE also contains a placeholder for item but the notify entity component does not allow
    # extra data keys yet, so this service is required to be able to invoke URGENT_MESSAGE with the item field.

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        "send_message",
        make_entity_service_schema(
            {
                vol.Required(ATTR_NOTIFICATION_TYPE): vol.All(
                    vol.Upper, cv.enum(BringNotificationType)
                ),
                vol.Optional(ATTR_ITEM_NAME): cv.string,
            }
        ),
        "async_send_bring_message",
    )


class BringNotify(NotifyEntity):
    """Representation of a Bring notify entity."""

    _attr_has_entity_name = False
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: BringDataUpdateCoordinator,
        bring_list: BringData,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the Notify entity."""
        if TYPE_CHECKING:
            assert entry.unique_id

        self.coordinator = coordinator
        self._list_uuid = bring_list["listUuid"]
        self._attr_name = bring_list["name"]

        self._attr_unique_id = f"{entry.unique_id}_{self._list_uuid}"
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, entry.unique_id)},
            manufacturer=MANUFACTURER,
            model=SERVICE_NAME,
        )

    async def async_send_message(self, message: str) -> None:
        """Send a push notification to members of a shared bring list."""
        try:
            await self.async_send_bring_message(message=BringNotificationType[message])
        except KeyError as e:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="notify_invalid_message_type",
                translation_placeholders={
                    "notification_types": ", ".join(
                        x.value for x in BringNotificationType
                    ),
                },
            ) from e

    async def async_send_bring_message(
        self,
        message: BringNotificationType,
        item: str | None = None,
    ) -> None:
        """Send a push notification to members of a shared bring list."""

        try:
            await self.coordinator.bring.notify(self._list_uuid, message, item)
        except BringRequestException as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="notify_request_failed",
            ) from e
        except ValueError as e:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="notify_missing_argument_item",
            ) from e
