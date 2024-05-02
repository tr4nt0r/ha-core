"""Support for Habitica sensors."""

from __future__ import annotations

from collections import namedtuple
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from http import HTTPStatus
import logging
from typing import TYPE_CHECKING, Any

from aiohttp import ClientResponseError

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import Throttle

from .const import DOMAIN, MANUFACTURER, NAME

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=15)


@dataclass(kw_only=True, frozen=True)
class HabitipySensorEntityDescription(SensorEntityDescription):
    """Habitipy Sensor Description."""

    value_path: list[str]


class HabitipySensorEntity(StrEnum):
    """Habitipy Entities."""

    DISPLAY_NAME = "display_name"
    HEALTH = "health"
    MANA = "mana"
    MANA_MAX = "mana_max"
    EXPERIENCE = "experience"
    EXPERIENCE_MAX = "experience_max"
    LEVEL = "level"
    GOLD = "gold"
    CLASS = "class"


SENSOR_DESCRIPTIONS: dict[str, HabitipySensorEntityDescription] = {
    HabitipySensorEntity.DISPLAY_NAME: HabitipySensorEntityDescription(
        key=HabitipySensorEntity.DISPLAY_NAME,
        translation_key=HabitipySensorEntity.DISPLAY_NAME,
        value_path=["profile", "name"],
    ),
    HabitipySensorEntity.HEALTH: HabitipySensorEntityDescription(
        key=HabitipySensorEntity.HEALTH,
        translation_key=HabitipySensorEntity.HEALTH,
        native_unit_of_measurement="HP",
        suggested_display_precision=0,
        value_path=["stats", "hp"],
    ),
    HabitipySensorEntity.HEALTH_MAX: HabitipySensorEntityDescription(
        key=HabitipySensorEntity.HEALTH_MAX,
        translation_key=HabitipySensorEntity.HEALTH_MAX,
        native_unit_of_measurement="HP",
        entity_registry_enabled_default=False,
        value_path=["stats", "maxHealth"],
    ),
    HabitipySensorEntity.MANA: HabitipySensorEntityDescription(
        key=HabitipySensorEntity.MANA,
        translation_key=HabitipySensorEntity.MANA,
        native_unit_of_measurement="MP",
        suggested_display_precision=0,
        value_path=["stats", "mp"],
    ),
    HabitipySensorEntity.MANA_MAX: HabitipySensorEntityDescription(
        key=HabitipySensorEntity.MANA_MAX,
        translation_key=HabitipySensorEntity.MANA_MAX,
        native_unit_of_measurement="MP",
        value_path=["stats", "maxMP"],
    ),
    HabitipySensorEntity.EXPERIENCE: HabitipySensorEntityDescription(
        key=HabitipySensorEntity.EXPERIENCE,
        translation_key=HabitipySensorEntity.EXPERIENCE,
        native_unit_of_measurement="XP",
        value_path=["stats", "exp"],
    ),
    HabitipySensorEntity.EXPERIENCE_MAX: HabitipySensorEntityDescription(
        key=HabitipySensorEntity.EXPERIENCE_MAX,
        translation_key=HabitipySensorEntity.EXPERIENCE_MAX,
        native_unit_of_measurement="XP",
        value_path=["stats", "toNextLevel"],
    ),
    HabitipySensorEntity.LEVEL: HabitipySensorEntityDescription(
        key=HabitipySensorEntity.LEVEL,
        translation_key=HabitipySensorEntity.LEVEL,
        value_path=["stats", "lvl"],
    ),
    HabitipySensorEntity.GOLD: HabitipySensorEntityDescription(
        key=HabitipySensorEntity.GOLD,
        translation_key=HabitipySensorEntity.GOLD,
        native_unit_of_measurement="GP",
        suggested_display_precision=2,
        value_path=["stats", "gp"],
    ),
    HabitipySensorEntity.CLASS: HabitipySensorEntityDescription(
        key=HabitipySensorEntity.CLASS,
        translation_key=HabitipySensorEntity.CLASS,
        value_path=["stats", "class"],
        device_class=SensorDeviceClass.ENUM,
        options=["warrior", "healer", "wizard", "rogue"],
    ),
}

SensorType = namedtuple("SensorType", ["name", "icon", "unit", "path"])
TASKS_TYPES = {
    "habits": SensorType(
        "Habits", "mdi:clipboard-list-outline", "n_of_tasks", ["habits"]
    ),
    "dailys": SensorType(
        "Dailys", "mdi:clipboard-list-outline", "n_of_tasks", ["dailys"]
    ),
    "todos": SensorType("TODOs", "mdi:clipboard-list-outline", "n_of_tasks", ["todos"]),
    "rewards": SensorType(
        "Rewards", "mdi:clipboard-list-outline", "n_of_tasks", ["rewards"]
    ),
}

TASKS_MAP_ID = "id"
TASKS_MAP = {
    "repeat": "repeat",
    "challenge": "challenge",
    "group": "group",
    "frequency": "frequency",
    "every_x": "everyX",
    "streak": "streak",
    "counter_up": "counterUp",
    "counter_down": "counterDown",
    "next_due": "nextDue",
    "yester_daily": "yesterDaily",
    "completed": "completed",
    "collapse_checklist": "collapseChecklist",
    "type": "type",
    "notes": "notes",
    "tags": "tags",
    "value": "value",
    "priority": "priority",
    "start_date": "startDate",
    "days_of_month": "daysOfMonth",
    "weeks_of_month": "weeksOfMonth",
    "created_at": "createdAt",
    "text": "text",
    "is_due": "isDue",
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the habitica sensors."""

    name = config_entry.data[CONF_NAME]
    sensor_data = HabitipyData(hass.data[DOMAIN][config_entry.entry_id])
    await sensor_data.update()

    entities: list[SensorEntity] = [
        HabitipySensor(sensor_data, description, config_entry)
        for description in SENSOR_DESCRIPTIONS.values()
    ]
    entities.extend(
        HabitipyTaskSensor(name, task_type, sensor_data, config_entry)
        for task_type in TASKS_TYPES
    )
    async_add_entities(entities, True)


class HabitipyData:
    """Habitica API user data cache."""

    tasks: dict[str, Any]

    def __init__(self, api) -> None:
        """Habitica API user data cache."""
        self.api = api
        self.data = None
        self.tasks = {}

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def update(self):
        """Get a new fix from Habitica servers."""
        try:
            self.data = await self.api.user.get()
        except ClientResponseError as error:
            if error.status == HTTPStatus.TOO_MANY_REQUESTS:
                _LOGGER.warning(
                    (
                        "Sensor data update for %s has too many API requests;"
                        " Skipping the update"
                    ),
                    DOMAIN,
                )
            else:
                _LOGGER.error(
                    "Count not update sensor data for %s (%s)",
                    DOMAIN,
                    error,
                )

        for task_type in TASKS_TYPES:
            try:
                self.tasks[task_type] = await self.api.tasks.user.get(type=task_type)
            except ClientResponseError as error:
                if error.status == HTTPStatus.TOO_MANY_REQUESTS:
                    _LOGGER.warning(
                        (
                            "Sensor data update for %s has too many API requests;"
                            " Skipping the update"
                        ),
                        DOMAIN,
                    )
                else:
                    _LOGGER.error(
                        "Count not update sensor data for %s (%s)",
                        DOMAIN,
                        error,
                    )


class HabitipySensor(SensorEntity):
    """A generic Habitica sensor."""

    _attr_has_entity_name = True
    entity_description: HabitipySensorEntityDescription

    def __init__(
        self,
        coordinator,
        entity_description: HabitipySensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize a generic Habitica sensor."""
        super().__init__()
        if TYPE_CHECKING:
            assert entry.unique_id
        self.coordinator = coordinator
        self.entity_description = entity_description
        self._attr_unique_id = f"{entry.unique_id}_{entity_description.key}"
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            manufacturer=MANUFACTURER,
            model=NAME,
            name=entry.data[CONF_NAME],
            configuration_url=entry.data[CONF_URL],
            identifiers={(DOMAIN, entry.unique_id)},
        )

    async def async_update(self) -> None:
        """Update Sensor state."""
        await self.coordinator.update()
        data = self.coordinator.data
        for element in self.entity_description.value_path:
            data = data[element]
        self._attr_native_value = data


class HabitipyTaskSensor(SensorEntity):
    """A Habitica task sensor."""

    def __init__(self, name, task_name, updater, entry):
        """Initialize a generic Habitica task."""
        self._name = name
        self._task_name = task_name
        self._task_type = TASKS_TYPES[task_name]
        self._state = None
        self._updater = updater
        self._attr_unique_id = f"{entry.unique_id}_{task_name}"
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            manufacturer=MANUFACTURER,
            model=NAME,
            name=entry.data[CONF_NAME],
            configuration_url=entry.data[CONF_URL],
            identifiers={(DOMAIN, entry.unique_id)},
        )

    async def async_update(self) -> None:
        """Update Condition and Forecast."""
        await self._updater.update()
        all_tasks = self._updater.tasks
        for element in self._task_type.path:
            tasks_length = len(all_tasks[element])
        self._state = tasks_length

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return self._task_type.icon

    @property
    def name(self):
        """Return the name of the task."""
        return f"{DOMAIN}_{self._name}_{self._task_name}"

    @property
    def native_value(self):
        """Return the state of the device."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes of all user tasks."""
        if self._updater.tasks is not None:
            all_received_tasks = self._updater.tasks
            for element in self._task_type.path:
                received_tasks = all_received_tasks[element]
            attrs = {}

            # Map tasks to TASKS_MAP
            for received_task in received_tasks:
                task_id = received_task[TASKS_MAP_ID]
                task = {}
                for map_key, map_value in TASKS_MAP.items():
                    if value := received_task.get(map_value):
                        task[map_key] = value
                attrs[task_id] = task
            return attrs

    @property
    def native_unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._task_type.unit
