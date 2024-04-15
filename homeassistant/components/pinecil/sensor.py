"""Platform for sensor integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.bluetooth.passive_update_coordinator import (
    PassiveBluetoothCoordinatorEntity,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, OHM, OPERATING_MODES, POWER_SOURCES, PinecilEntity
from .coordinator import PinecilActiveBluetoothDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class PinecilSensorEntityDescription(SensorEntityDescription):
    """Describes Pinecil sensor entity."""

    value_fn: Callable[[Any], Any]


SENSOR_DESCRIPTIONS: dict[str, PinecilSensorEntityDescription] = {
    PinecilEntity.LIVE_TEMP: PinecilSensorEntityDescription(
        key=PinecilEntity.LIVE_TEMP,
        translation_key=PinecilEntity.LIVE_TEMP,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("LiveTemp"),
    ),
    PinecilEntity.DC_VOLTAGE: PinecilSensorEntityDescription(
        key=PinecilEntity.DC_VOLTAGE,
        translation_key=PinecilEntity.DC_VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("Voltage") / 10,
    ),
    PinecilEntity.HANDLETEMP: PinecilSensorEntityDescription(
        key=PinecilEntity.HANDLETEMP,
        translation_key=PinecilEntity.HANDLETEMP,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("HandleTemp") / 10,
    ),
    PinecilEntity.PWMLEVEL: PinecilSensorEntityDescription(
        key=PinecilEntity.PWMLEVEL,
        translation_key=PinecilEntity.PWMLEVEL,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("PWMLevel") * 100 / 255.0,
    ),
    PinecilEntity.POWER_SRC: PinecilSensorEntityDescription(
        key=PinecilEntity.POWER_SRC,
        translation_key=PinecilEntity.POWER_SRC,
        device_class=SensorDeviceClass.ENUM,
        options=POWER_SOURCES,
        value_fn=lambda data: POWER_SOURCES[data.get("PowerSource")],
    ),
    PinecilEntity.TIP_RESISTANCE: PinecilSensorEntityDescription(
        key=PinecilEntity.TIP_RESISTANCE,
        translation_key=PinecilEntity.TIP_RESISTANCE,
        native_unit_of_measurement=OHM,
        value_fn=lambda data: data.get("TipResistance") / 10,
    ),
    PinecilEntity.UPTIME: PinecilSensorEntityDescription(
        key=PinecilEntity.UPTIME,
        translation_key=PinecilEntity.UPTIME,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: int(data.get("Uptime") / 10),
    ),
    PinecilEntity.MOVEMENT_TIME: PinecilSensorEntityDescription(
        key=PinecilEntity.MOVEMENT_TIME,
        translation_key=PinecilEntity.MOVEMENT_TIME,
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: int(data.get("MovementTime") / 10),
    ),
    PinecilEntity.MAX_TIP_TEMP_ABILITY: PinecilSensorEntityDescription(
        key=PinecilEntity.MAX_TIP_TEMP_ABILITY,
        translation_key=PinecilEntity.MAX_TIP_TEMP_ABILITY,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        icon="mdi:thermometer-alert",
        value_fn=lambda data: data.get("MaxTipTempAbility"),
    ),
    PinecilEntity.TIP_VOLTAGE: PinecilSensorEntityDescription(
        key=PinecilEntity.TIP_VOLTAGE,
        translation_key=PinecilEntity.TIP_VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda data: data.get("uVoltsTip") / 1000,
    ),
    PinecilEntity.HALL_SENSOR: PinecilSensorEntityDescription(
        key=PinecilEntity.HALL_SENSOR,
        translation_key=PinecilEntity.HALL_SENSOR,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.get("HallSensor"),
    ),
    PinecilEntity.OPERATING_MODE: PinecilSensorEntityDescription(
        key=PinecilEntity.OPERATING_MODE,
        translation_key=PinecilEntity.OPERATING_MODE,
        device_class=SensorDeviceClass.ENUM,
        options=OPERATING_MODES,
        value_fn=lambda data: OPERATING_MODES[data.get("OperatingMode")],
    ),
    PinecilEntity.ESTIMATED_POWER: PinecilSensorEntityDescription(
        key=PinecilEntity.ESTIMATED_POWER,
        translation_key=PinecilEntity.ESTIMATED_POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("Watts") / 10,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        PinecilSensor(coordinator, description, entry)
        for description in SENSOR_DESCRIPTIONS.values()
    )


class PinecilSensor(PassiveBluetoothCoordinatorEntity, SensorEntity):
    """Implementation of a Pinecil sensor."""

    _attr_has_entity_name = True
    entity_description: PinecilSensorEntityDescription

    def __init__(
        self,
        coordinator: PinecilActiveBluetoothDataUpdateCoordinator,
        entity_description: PinecilSensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        assert entry.unique_id
        self.entity_description = entity_description
        self._attr_unique_id = f"{entry.unique_id}_{entity_description.key}"
        self.coordinator = coordinator
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> float | int | str | None:
        """Return sensor state."""

        return self.coordinator.device.data.get(self.entity_description.key)
