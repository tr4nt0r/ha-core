"""Platform for sensor integration."""

from __future__ import annotations

from enum import StrEnum

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_ADDRESS,
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class PinecilSensorEntity(StrEnum):
    """pyLoad Sensor Entities."""

    LIVE_TEMP = "live_temperature"
    DC_VOLTAGE = "voltage"
    HANDLETEMP = "handle_temperature"
    PWMLEVEL = "power_pwm_level"
    POWER_SRC = "power_source"
    TIP_RESISTANCE = "tip_resistance"
    UPTIME = "uptime"
    MOVEMENT_TIME = "movemenet_time"
    MAX_TIP_TEMP_ABILITY = "max_tip_temp_ability"
    TIP_VOLTAGE = "tip_voltage"
    HALL_SENSOR = "hall_sensor"
    OPERATING_MODE = "operating_mode"
    ESTIMATED_POWER = "estimated_power"


SENSOR_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    PinecilSensorEntity.LIVE_TEMP: SensorEntityDescription(
        key=PinecilSensorEntity.LIVE_TEMP,
        translation_key=PinecilSensorEntity.LIVE_TEMP,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PinecilSensorEntity.DC_VOLTAGE: SensorEntityDescription(
        key=PinecilSensorEntity.DC_VOLTAGE,
        translation_key=PinecilSensorEntity.DC_VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PinecilSensorEntity.HANDLETEMP: SensorEntityDescription(
        key=PinecilSensorEntity.HANDLETEMP,
        translation_key=PinecilSensorEntity.HANDLETEMP,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PinecilSensorEntity.PWMLEVEL: SensorEntityDescription(
        key=PinecilSensorEntity.PWMLEVEL,
        translation_key=PinecilSensorEntity.PWMLEVEL,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PinecilSensorEntity.POWER_SRC: SensorEntityDescription(
        key=PinecilSensorEntity.POWER_SRC,
        translation_key=PinecilSensorEntity.POWER_SRC,
        device_class=SensorDeviceClass.ENUM,
    ),
    PinecilSensorEntity.TIP_RESISTANCE: SensorEntityDescription(
        key=PinecilSensorEntity.TIP_RESISTANCE,
        translation_key=PinecilSensorEntity.TIP_RESISTANCE,
        native_unit_of_measurement="Ω",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PinecilSensorEntity.UPTIME: SensorEntityDescription(
        key=PinecilSensorEntity.UPTIME,
        translation_key=PinecilSensorEntity.UPTIME,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PinecilSensorEntity.MOVEMENT_TIME: SensorEntityDescription(
        key=PinecilSensorEntity.MOVEMENT_TIME,
        translation_key=PinecilSensorEntity.MOVEMENT_TIME,
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PinecilSensorEntity.MAX_TIP_TEMP_ABILITY: SensorEntityDescription(
        key=PinecilSensorEntity.MAX_TIP_TEMP_ABILITY,
        translation_key=PinecilSensorEntity.MAX_TIP_TEMP_ABILITY,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer-alert",
    ),
    PinecilSensorEntity.TIP_VOLTAGE: SensorEntityDescription(
        key=PinecilSensorEntity.TIP_VOLTAGE,
        translation_key=PinecilSensorEntity.TIP_VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PinecilSensorEntity.HALL_SENSOR: SensorEntityDescription(
        key=PinecilSensorEntity.HALL_SENSOR,
        translation_key=PinecilSensorEntity.HALL_SENSOR,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    PinecilSensorEntity.OPERATING_MODE: SensorEntityDescription(
        key=PinecilSensorEntity.OPERATING_MODE,
        translation_key=PinecilSensorEntity.OPERATING_MODE,
        device_class=SensorDeviceClass.ENUM,
    ),
    PinecilSensorEntity.ESTIMATED_POWER: SensorEntityDescription(
        key=PinecilSensorEntity.ESTIMATED_POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        PinecilSensor(coordinator, description, entry)
        for description in SENSOR_DESCRIPTIONS.values()
    )


class PinecilSensor(CoordinatorEntity, SensorEntity):
    """Implementation of a Pinecil sensor."""

    _attr_has_entity_name = True
    entity_description: SensorEntityDescription

    def __init__(
        self,
        coordinator: PinecilCoordinator,
        entity_description: SensorEntityDescription,
        entry: ConfigEntry,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = f"{entry.unique_id}_{entity_description.key}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data[CONF_ADDRESS])},
            manufacturer="Pine64",
            name="Pinecil",
            hw_version="V2",
            sw_version="2.22",
        )

    @property
    def native_value(self) -> float | None:
        """Return sensor state."""
        return self.coordinator[self.entity_description.key]
