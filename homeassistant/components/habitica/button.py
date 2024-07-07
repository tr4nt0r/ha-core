"""Habitica button platform."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from aiohttp import ClientResponseError

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import CONF_NAME, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HabiticaConfigEntry
from .const import DOMAIN, MANUFACTURER, NAME
from .coordinator import HabiticaData, HabiticaDataUpdateCoordinator


@dataclass(kw_only=True, frozen=True)
class HabiticaButtonEntityDescription(ButtonEntityDescription):
    """Describes Habitica button entity."""

    press_fn: Callable[[HabiticaDataUpdateCoordinator], Any]
    available_fn: Callable[[HabiticaData], bool] | None = None


class HabitipyButtonEntity(StrEnum):
    """Habitica button entities."""

    RUN_CRON = "run_cron"
    BUY_HEALTH_POTION = "buy_health_potion"
    FIREBALL = "fireball"
    MPHEAL = "mpheal"
    EARTH = "earth"
    FROST = "frost"
    DEFENSIVE_STANCE = "defensive_stance"
    VALOROUS_PRESENCE = "valorous_presence"
    INTIMIDATE = "intimidate"
    TOOLS_OF_TRADE = "tools_of_trade"
    STEALTH = "stealth"
    HEAL = "heal"
    PROTECT_AURA = "protect_aura"
    BRIGHTNESS = "brightness"
    HEAL_ALL = "heal_all"


BUTTON_DESCRIPTIONS: tuple[HabiticaButtonEntityDescription, ...] = (
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.RUN_CRON,
        translation_key=HabitipyButtonEntity.RUN_CRON,
        press_fn=lambda coordinator: coordinator.api.cron.post(),
        available_fn=lambda data: data.user["needsCron"],
    ),
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.BUY_HEALTH_POTION,
        translation_key=HabitipyButtonEntity.BUY_HEALTH_POTION,
        press_fn=lambda coordinator: coordinator.api["user"][
            "buy-health-potion"
        ].post(),
    ),
)

WIZARD_SKILLS: tuple[HabiticaButtonEntityDescription, ...] = (
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.FIREBALL,
        translation_key=HabitipyButtonEntity.FIREBALL,
        press_fn=lambda coordinator: coordinator.api.user.class_.cast[
            "fireball"
        ].post(),
        available_fn=lambda data: data.user["stats"]["lvl"] >= 11,
    ),
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.MPHEAL,
        translation_key=HabitipyButtonEntity.MPHEAL,
        press_fn=lambda coordinator: coordinator.api.user.class_.cast["mpheal"].post(),
        available_fn=lambda data: data.user["stats"]["lvl"] >= 12,
    ),
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.EARTH,
        translation_key=HabitipyButtonEntity.EARTH,
        press_fn=lambda coordinator: coordinator.api.user.class_.cast["earth"].post(),
        available_fn=lambda data: data.user["stats"]["lvl"] >= 13,
    ),
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.FROST,
        translation_key=HabitipyButtonEntity.FROST,
        press_fn=lambda coordinator: coordinator.api.user.class_.cast["frost"].post(),
        available_fn=lambda data: data.user["stats"]["lvl"] >= 14,
    ),
)

WARRIOR_SKILLS: tuple[HabiticaButtonEntityDescription, ...] = (
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.DEFENSIVE_STANCE,
        translation_key=HabitipyButtonEntity.DEFENSIVE_STANCE,
        press_fn=lambda coordinator: coordinator.api.user.class_.cast[
            "defensiveStance"
        ].post(),
        available_fn=lambda data: data.user["stats"]["lvl"] >= 12,
    ),
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.VALOROUS_PRESENCE,
        translation_key=HabitipyButtonEntity.VALOROUS_PRESENCE,
        press_fn=lambda coordinator: coordinator.api.user.class_.cast[
            "valorousPresence"
        ].post(),
        available_fn=lambda data: data.user["stats"]["lvl"] >= 13,
    ),
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.INTIMIDATE,
        translation_key=HabitipyButtonEntity.INTIMIDATE,
        press_fn=lambda coordinator: coordinator.api.user.class_.cast[
            "intimidate"
        ].post(),
        available_fn=lambda data: data.user["stats"]["lvl"] >= 14,
    ),
)

ROGUE_SKILLS: tuple[HabiticaButtonEntityDescription, ...] = (
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.TOOLS_OF_TRADE,
        translation_key=HabitipyButtonEntity.TOOLS_OF_TRADE,
        press_fn=lambda coordinator: coordinator.api.user.class_.cast[
            "toolsOfTrade"
        ].post(),
        available_fn=lambda data: data.user["stats"]["lvl"] >= 13,
    ),
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.STEALTH,
        translation_key=HabitipyButtonEntity.STEALTH,
        press_fn=lambda coordinator: coordinator.api.user.class_.cast["stealth"].post(),
        available_fn=lambda data: data.user["stats"]["lvl"] >= 14,
    ),
)

HEALER_SKILLS: tuple[HabiticaButtonEntityDescription, ...] = (
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.HEAL,
        translation_key=HabitipyButtonEntity.HEAL,
        press_fn=lambda coordinator: coordinator.api.user.class_.cast["heal"].post(),
        available_fn=lambda data: data.user["stats"]["lvl"] >= 11,
    ),
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.BRIGHTNESS,
        translation_key=HabitipyButtonEntity.BRIGHTNESS,
        press_fn=lambda coordinator: coordinator.api.user.class_.cast[
            "brightness"
        ].post(),
        available_fn=lambda data: data.user["stats"]["lvl"] >= 12,
    ),
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.PROTECT_AURA,
        translation_key=HabitipyButtonEntity.PROTECT_AURA,
        press_fn=lambda coordinator: coordinator.api.user.class_.cast[
            "protectAura"
        ].post(),
        available_fn=lambda data: data.user["stats"]["lvl"] >= 13,
    ),
    HabiticaButtonEntityDescription(
        key=HabitipyButtonEntity.HEAL_ALL,
        translation_key=HabitipyButtonEntity.HEAL_ALL,
        press_fn=lambda coordinator: coordinator.api.user.class_.cast["healAll"].post(),
        available_fn=lambda data: data.user["stats"]["lvl"] >= 14,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HabiticaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up buttons from a config entry."""

    coordinator = entry.runtime_data

    async_add_entities(
        HabiticaButton(coordinator, description) for description in BUTTON_DESCRIPTIONS
    )
    if coordinator.data.user["stats"]["class"] == "wizard":
        async_add_entities(
            HabiticaButton(coordinator, description) for description in WIZARD_SKILLS
        )
    if coordinator.data.user["stats"]["class"] == "warrior":
        async_add_entities(
            HabiticaButton(coordinator, description) for description in WARRIOR_SKILLS
        )
    if coordinator.data.user["stats"]["class"] == "rogue":
        async_add_entities(
            HabiticaButton(coordinator, description) for description in ROGUE_SKILLS
        )
    if coordinator.data.user["stats"]["class"] == "healer":
        async_add_entities(
            HabiticaButton(coordinator, description) for description in HEALER_SKILLS
        )


class HabiticaButton(CoordinatorEntity[HabiticaDataUpdateCoordinator], ButtonEntity):
    """Representation of a Habitica button."""

    _attr_has_entity_name = True
    entity_description: HabiticaButtonEntityDescription

    def __init__(
        self,
        coordinator: HabiticaDataUpdateCoordinator,
        entity_description: HabiticaButtonEntityDescription,
    ) -> None:
        """Initialize a Habitica button."""
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
            configuration_url=coordinator.config_entry.data[CONF_URL],
            identifiers={(DOMAIN, coordinator.config_entry.unique_id)},
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        try:
            await self.entity_description.press_fn(self.coordinator)
        except ClientResponseError as e:
            if e.status == HTTPStatus.TOO_MANY_REQUESTS:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="setup_rate_limit_exception",
                ) from e
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="service_call_exception",
            ) from e

    @property
    def available(self) -> bool:
        """Is entity available."""
        if self.entity_description.available_fn:
            return self.entity_description.available_fn(self.coordinator.data)
        return True
