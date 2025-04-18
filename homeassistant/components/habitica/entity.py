"""Base entity for Habitica."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from habiticalib import ContentData
from habiticalib.typedefs import UserData
from yarl import URL

from homeassistant.const import CONF_NAME, CONF_URL
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, NAME
from .coordinator import (
    HabiticaDataUpdateCoordinator,
    HabiticaPartyCoordinator,
    HabiticaRuntimeData,
)


class HabiticaBase(CoordinatorEntity[HabiticaDataUpdateCoordinator]):
    """Base Habitica entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HabiticaDataUpdateCoordinator,
        entity_description: EntityDescription,
    ) -> None:
        """Initialize a Habitica entity."""
        super().__init__(coordinator)
        if TYPE_CHECKING:
            assert coordinator.config_entry.unique_id
        self.entity_description = entity_description
        self._attr_unique_id = (
            f"{coordinator.config_entry.unique_id}_{entity_description.key}"
        )
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            manufacturer=MANUFACTURER,
            model=NAME,
            name=coordinator.config_entry.data[CONF_NAME],
            configuration_url=(
                URL(coordinator.config_entry.data[CONF_URL])
                / "profile"
                / coordinator.config_entry.unique_id
            ),
            identifiers={(DOMAIN, coordinator.config_entry.unique_id)},
        )


class HabiticaPartyMember(CoordinatorEntity[HabiticaPartyCoordinator]):
    """Habitica Party Member Base entity."""

    _attr_has_entity_name = True
    member: UserData
    content: ContentData

    def __init__(
        self,
        coordinators: HabiticaRuntimeData,
        entity_description: EntityDescription,
        user_id: UUID,
    ) -> None:
        """Initialize a Habitica entity."""
        super().__init__(coordinators.party)
        if TYPE_CHECKING:
            assert self.coordinator.config_entry.unique_id
        self.entity_description = entity_description
        self.user_id = user_id
        self._attr_unique_id = f"{user_id!s}_{entity_description.key}"
        self.member = next(i for i in self.coordinator.data.members if i.id is user_id)
        self.content = coordinators.me.content
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            manufacturer=MANUFACTURER,
            model=NAME,
            name=self.member.profile.name,
            configuration_url=(
                URL(self.coordinator.config_entry.data[CONF_URL])
                / "profile"
                / str(user_id)
            ),
            identifiers={(DOMAIN, str(user_id))},
        )
