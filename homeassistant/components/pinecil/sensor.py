"""Sensor platform for Pinecil integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pynecil import LiveDataResponse, OperatingMode, PowerSource

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from . import PinecilConfigEntry
from .const import OHM, PinecilEntity
from .entity import PinecilBaseEntity


@dataclass(frozen=True, kw_only=True)
class PinecilSensorEntityDescription(SensorEntityDescription):
    """Describes Pinecil sensor entity."""

    value_fn: Callable[[LiveDataResponse], Any]


SENSOR_DESCRIPTIONS: tuple[PinecilSensorEntityDescription, ...] = (
    PinecilSensorEntityDescription(
        key=PinecilEntity.LIVE_TEMP,
        translation_key=PinecilEntity.LIVE_TEMP,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.live_temp,
    ),
    PinecilSensorEntityDescription(
        key=PinecilEntity.DC_VOLTAGE,
        translation_key=PinecilEntity.DC_VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.dc_input,
    ),
    PinecilSensorEntityDescription(
        key=PinecilEntity.HANDLETEMP,
        translation_key=PinecilEntity.HANDLETEMP,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.handle_temp,
    ),
    PinecilSensorEntityDescription(
        key=PinecilEntity.PWMLEVEL,
        translation_key=PinecilEntity.PWMLEVEL,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.power_level,
    ),
    PinecilSensorEntityDescription(
        key=PinecilEntity.POWER_SRC,
        translation_key=PinecilEntity.POWER_SRC,
        device_class=SensorDeviceClass.ENUM,
        options=[item.lower() for item in PowerSource._member_names_],
        value_fn=lambda data: data.power_src.name.lower() if data.power_src else None,
    ),
    PinecilSensorEntityDescription(
        key=PinecilEntity.TIP_RESISTANCE,
        translation_key=PinecilEntity.TIP_RESISTANCE,
        native_unit_of_measurement=OHM,
        value_fn=lambda data: data.tip_res,
    ),
    PinecilSensorEntityDescription(
        key=PinecilEntity.UPTIME,
        translation_key=PinecilEntity.UPTIME,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.uptime,
    ),
    PinecilSensorEntityDescription(
        key=PinecilEntity.MOVEMENT_TIME,
        translation_key=PinecilEntity.MOVEMENT_TIME,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.movement,
    ),
    PinecilSensorEntityDescription(
        key=PinecilEntity.MAX_TIP_TEMP_ABILITY,
        translation_key=PinecilEntity.MAX_TIP_TEMP_ABILITY,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda data: data.max_temp,
    ),
    PinecilSensorEntityDescription(
        key=PinecilEntity.TIP_VOLTAGE,
        translation_key=PinecilEntity.TIP_VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda data: data.raw_tip,
    ),
    PinecilSensorEntityDescription(
        key=PinecilEntity.HALL_SENSOR,
        translation_key=PinecilEntity.HALL_SENSOR,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.hall_sensor,
    ),
    PinecilSensorEntityDescription(
        key=PinecilEntity.OPERATING_MODE,
        translation_key=PinecilEntity.OPERATING_MODE,
        device_class=SensorDeviceClass.ENUM,
        options=[item.lower() for item in OperatingMode._member_names_],
        value_fn=lambda data: data.op_mode.name.lower() if data.op_mode else None,
    ),
    PinecilSensorEntityDescription(
        key=PinecilEntity.ESTIMATED_POWER,
        translation_key=PinecilEntity.ESTIMATED_POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.est_power,
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
        PinecilSensor(coordinator, description) for description in SENSOR_DESCRIPTIONS
    )


class PinecilSensor(PinecilBaseEntity, SensorEntity):
    """Implementation of a Pinecil sensor."""

    _attr_has_entity_name = True
    entity_description: PinecilSensorEntityDescription

    @property
    def native_value(self) -> StateType:
        """Return sensor state."""
        return self.entity_description.value_fn(self.coordinator.data)
