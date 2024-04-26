"""Todo platform for the Habitica integration."""

from __future__ import annotations

import datetime
from enum import StrEnum
import logging
from typing import TYPE_CHECKING, Any, Final

from aiohttp import ClientResponseError

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, MANUFACTURER, NAME
from .coordinator import HabitipyData

_LOGGER = logging.getLogger(__name__)

CHECKLIST_DELIMITER: Final = "<!--BEGIN_CHECKLIST-->"


class HabiticaTodoList(StrEnum):
    """Habitica Entities."""

    HABITS = "habits"
    DAILIES = "dailies"
    TODOS = "todos"
    REWARDS = "rewards"


class HabiticaTaskType(StrEnum):
    """Habitica Entities."""

    HABIT = "habit"
    DAILY = "daily"
    TODO = "todo"
    REWARD = "reward"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor from a config entry created in the integrations UI."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    await coordinator.update()

    async_add_entities(
        [
            HabiticaHabitsListEntity(coordinator, config_entry),
            HabiticaTodosListEntity(coordinator, config_entry),
            HabiticaDailiesListEntity(coordinator, config_entry),
        ],
        True,
    )


def format_description(task: dict[str, Any]) -> str:
    """Format checklist as markdown."""
    checklist = "\n".join(
        [
            f"- {"[x]" if item["completed"] else "[ ]"} {item["text"]}"
            for item in task.get("checklist", {})
        ]
    )
    return f"{task["notes"]}{"\n" + CHECKLIST_DELIMITER + "\n" if task.get("checklist") else ""}{checklist}"


class BaseHabiticaListEntity(TodoListEntity):
    """Representation of Habitica task lists."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: HabitipyData, key: HabiticaTodoList, entry: ConfigEntry
    ) -> None:
        """Initialize HabiticaTodoListEntity."""
        if TYPE_CHECKING:
            assert entry.unique_id
        self.coordinator = coordinator
        self._attr_unique_id = f"{entry.unique_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            manufacturer=MANUFACTURER,
            model=NAME,
            name=entry.data[CONF_NAME],
            configuration_url=entry.data[CONF_URL],
            identifiers={(DOMAIN, entry.unique_id)},
        )

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete Habitica tasks."""
        for taskId in uids:
            try:
                await self.coordinator.api.tasks[taskId].delete()
            except ClientResponseError as e:
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key="delete_task_failed",
                ) from e

        await self.coordinator.update(no_throttle=True)
        self.async_schedule_update_ha_state()


class HabiticaTodosListEntity(BaseHabiticaListEntity):
    """List of Habitica todos."""

    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.SET_DUE_DATE_ON_ITEM
        | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
    )

    def __init__(self, coordinator: HabitipyData, entry: ConfigEntry) -> None:
        """Initialize HabiticaTodosListEntity."""
        super().__init__(coordinator, HabiticaTodoList.TODOS, entry)

    @property
    def todo_items(self) -> list[TodoItem]:
        """Return the todo items."""
        if not self.coordinator.tasks:
            return []

        return [
            *(
                TodoItem(
                    uid=task["id"],
                    summary=task["text"],
                    description=format_description(task),
                    due=(
                        datetime.datetime.fromisoformat(task.get("date")).date()
                        if task.get("date")
                        else None
                    ),
                    status=TodoItemStatus.NEEDS_ACTION
                    if not task["completed"]
                    else TodoItemStatus.COMPLETED,
                )
                for task in self.coordinator.tasks
                if task.get("type") == HabiticaTaskType.TODO
            ),
        ]

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Create a Habitica todo."""

        try:
            await self.coordinator.api.tasks.user.post(
                text=item.summary,
                type=HabiticaTaskType.TODO,
                notes=item.description,
                date=item.due.isoformat() if item.due else None,
            )
        except ClientResponseError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="todo_save_item_failed",
                translation_placeholders={"name": item.summary or ""},
            ) from e

        await self.coordinator.update(no_throttle=True)
        self.async_schedule_update_ha_state()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update a Habitica todo."""

        current_task = next(
            (i for i in self.coordinator.tasks if i["id"] == item.uid),
            None,
        )

        if TYPE_CHECKING:
            assert item.uid
            assert current_task

        try:
            await self.coordinator.api.tasks[item.uid].put(
                text=item.summary,
                notes=(item.description or "").split(CHECKLIST_DELIMITER, 1)[0].strip(),
                date=item.due.isoformat() if item.due else None,
            )
        except ClientResponseError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="todo_update_item_failed",  # TODO: add todo_update_item_failed to strings.json
                translation_placeholders={"name": item.summary or ""},
            ) from e

        try:
            # Score up or down if item status changed
            if (
                not current_task["completed"]
                and item.status == TodoItemStatus.COMPLETED
            ):
                await self.coordinator.api.tasks[item.uid].score["up"].post()
            elif (
                current_task["completed"] and item.status == TodoItemStatus.NEEDS_ACTION
            ):
                await self.coordinator.api.tasks[item.uid].score["down"].post()
            # TODO: handle scoring response, notify user about stat changes and item drops
        except ClientResponseError as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="todo_score_failed",  # TODO: add todo_score_failed to strings.json
                translation_placeholders={"name": item.summary or ""},
            ) from e

        await self.coordinator.update(no_throttle=True)
        self.async_schedule_update_ha_state()


class HabiticaDailiesListEntity(BaseHabiticaListEntity):
    """List of Habitica dailies."""

    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
        | TodoListEntityFeature.MOVE_TODO_ITEM
    )

    def __init__(self, coordinator: HabitipyData, entry: ConfigEntry) -> None:
        """Initialize HabiticaDailiesListEntity."""
        super().__init__(coordinator, HabiticaTodoList.DAILIES, entry)

    @property
    def todo_items(self) -> list[TodoItem]:
        """Return the todo items."""
        if not self.coordinator.tasks:
            return []

        return [
            *(
                TodoItem(
                    uid=task["id"],
                    summary=task["text"],
                    description=format_description(task),
                    # is due today or not today
                    due=(
                        dt_util.as_local(datetime.datetime.now()).date()
                        if task["isDue"] and not task["completed"]
                        else None
                    ),
                    status=TodoItemStatus.COMPLETED
                    if task["completed"]
                    else TodoItemStatus.NEEDS_ACTION,
                )
                for task in self.coordinator.tasks
                if task.get("type") == HabiticaTaskType.DAILY
            )
        ]


class HabiticaHabitsListEntity(BaseHabiticaListEntity):
    """List of Habitica habits."""

    _attr_supported_features = (
        TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
    )

    def __init__(self, coordinator: HabitipyData, entry: ConfigEntry) -> None:
        """Initialize HabiticaHabitsListEntity."""
        super().__init__(coordinator, HabiticaTodoList.HABITS, entry)

    @property
    def todo_items(self) -> list[TodoItem]:
        """Return the todo items."""
        if not self.coordinator.tasks:
            return []

        res = []
        for task in (
            task
            for task in self.coordinator.tasks
            if task["type"] == HabiticaTaskType.HABIT
        ):
            if task["up"]:
                res.append(
                    TodoItem(
                        uid=f"{task["id"]}_up",
                        summary=f"➕{task["text"]}",
                        description=format_description(task),
                        status=TodoItemStatus.NEEDS_ACTION,
                    )
                )
            if task["down"]:
                res.append(
                    TodoItem(
                        uid=f"{task["id"]}_down",
                        summary=f"➖{task["text"]}",
                        description=format_description(task),
                        status=TodoItemStatus.NEEDS_ACTION,
                    )
                )
        return res
