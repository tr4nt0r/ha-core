"""Number platform for Pinecil integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pynecil import CharSetting, LiveDataResponse, SettingsDataResponse

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import PinecilConfigEntry
from .const import MAX_TEMP, MIN_TEMP, PinecilEntity
from .coordinator import PinecilCoordinator


@dataclass(frozen=True, kw_only=True)
class PinecilNumberEntityDescription(NumberEntityDescription):
    """Describes Pinecil sensor entity."""

    value_fn: Callable[[LiveDataResponse, SettingsDataResponse], float | int | None]
    max_value_fn: Callable[[LiveDataResponse], float | int]
    set_key: CharSetting


SENSOR_DESCRIPTIONS: tuple[PinecilNumberEntityDescription, ...] = (
    PinecilNumberEntityDescription(
        key=PinecilEntity.SETPOINT_TEMP,
        translation_key=PinecilEntity.SETPOINT_TEMP,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        value_fn=lambda data, _: data.set_temp,
        set_key=CharSetting.SETPOINT_TEMP,
        mode=NumberMode.BOX,
        native_min_value=MIN_TEMP,
        native_step=5,
        max_value_fn=lambda data: min(data.max_temp or MAX_TEMP, MAX_TEMP),
    ),
    PinecilNumberEntityDescription(
        key=PinecilEntity.SLEEP_TEMP,
        translation_key=PinecilEntity.SLEEP_TEMP,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        value_fn=lambda _, settings: settings.get("sleep_temp"),
        set_key=CharSetting.SLEEP_TEMP,
        mode=NumberMode.BOX,
        native_min_value=MIN_TEMP,
        native_step=10,
        max_value_fn=lambda _: MAX_TEMP,
        entity_category=EntityCategory.CONFIG,
    ),
    PinecilNumberEntityDescription(
        key=PinecilEntity.BOOST_TEMP,
        translation_key=PinecilEntity.BOOST_TEMP,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        value_fn=lambda _, settings: settings.get("boost_temp"),
        set_key=CharSetting.BOOST_TEMP,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_step=10,
        max_value_fn=lambda _: MAX_TEMP,
        entity_category=EntityCategory.CONFIG,
    ),
    PinecilNumberEntityDescription(
        key=PinecilEntity.QC_MAX_VOLTAGE,
        translation_key=PinecilEntity.QC_MAX_VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=NumberDeviceClass.VOLTAGE,
        value_fn=lambda _, settings: settings.get("qc_ideal_voltage"),
        set_key=CharSetting.QC_IDEAL_VOLTAGE,
        mode=NumberMode.BOX,
        native_min_value=9.0,
        native_step=0.1,
        max_value_fn=lambda _: 22.0,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    PinecilNumberEntityDescription(
        key=PinecilEntity.PD_TIMEOUT,
        translation_key=PinecilEntity.PD_TIMEOUT,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        value_fn=lambda _, settings: settings.get("pd_negotiation_timeout"),
        set_key=CharSetting.PD_NEGOTIATION_TIMEOUT,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_step=1,
        max_value_fn=lambda _: 5.0,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    PinecilNumberEntityDescription(
        key=PinecilEntity.SHUTDOWN_TIMEOUT,
        translation_key=PinecilEntity.SHUTDOWN_TIMEOUT,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=NumberDeviceClass.DURATION,
        value_fn=lambda _, settings: settings.get("shutdown_time"),
        set_key=CharSetting.SHUTDOWN_TIME,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_step=1,
        max_value_fn=lambda _: 60,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    PinecilNumberEntityDescription(
        key=PinecilEntity.DISPLAY_BRIGHTNESS,
        translation_key=PinecilEntity.DISPLAY_BRIGHTNESS,
        value_fn=lambda _, settings: settings.get("display_brightness"),
        set_key=CharSetting.DISPLAY_BRIGHTNESS,
        mode=NumberMode.SLIDER,
        native_min_value=1,
        native_step=1,
        max_value_fn=lambda _: 5,
        entity_category=EntityCategory.CONFIG,
        entity_registry_visible_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PinecilConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    coordinator = entry.runtime_data

    async_add_entities(
        PinecilNumber(coordinator, description, entry)
        for description in SENSOR_DESCRIPTIONS
    )


class PinecilNumber(CoordinatorEntity[PinecilCoordinator], NumberEntity):
    """Implementation of a Pinecil sensor."""

    _attr_has_entity_name = True
    entity_description: PinecilNumberEntityDescription

    def __init__(
        self,
        coordinator: PinecilCoordinator,
        entity_description: PinecilNumberEntityDescription,
        entry: PinecilConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, context=entity_description.set_key)
        self.entity_description = entity_description
        self._attr_unique_id = f"{entry.unique_id}_{entity_description.key}"
        self.device_info = self.coordinator.device_info

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self.coordinator.pinecil.write(self.entity_description.set_key, value)
        await self.coordinator.save_settings()
        await self.coordinator.update_settings(no_throttle=True)

    @property
    def native_value(self) -> float | int | None:
        """Return sensor state."""
        return self.entity_description.value_fn(
            self.coordinator.data, self.coordinator.settings
        )

    @property
    def native_max_value(self) -> float:
        """Return sensor state."""
        return self.entity_description.max_value_fn(self.coordinator.data)
