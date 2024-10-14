"""Test Habitica sensor platform."""

from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import pytest

from homeassistant.components.habitica.const import (
    ATTR_CLEAR_REMINDER,
    ATTR_CONFIG_ENTRY,
    ATTR_FREQUENCY,
    ATTR_INTERVAL,
    ATTR_PRIORITY,
    ATTR_REMINDER_TIME,
    ATTR_REMOVE_REMINDER_TIME,
    ATTR_REPEAT,
    ATTR_REPEAT_MONTHLY,
    ATTR_START_DATE,
    ATTR_STREAK,
    ATTR_TASK,
    DEFAULT_URL,
    DOMAIN,
    SERVICE_UPDATE_DAILY,
)
from homeassistant.components.todo import ATTR_DESCRIPTION, ATTR_RENAME
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from .conftest import mock_called_with

from tests.common import MockConfigEntry
from tests.test_util.aiohttp import AiohttpClientMocker


@pytest.fixture(autouse=True)
def services_only() -> Generator[None]:
    """Enable only services."""
    with patch(
        "homeassistant.components.habitica.PLATFORMS",
        [],
    ):
        yield


@pytest.mark.parametrize(
    ("service_data", "expected"),
    [
        (
            {ATTR_TASK: "Zahnseide benutzen"},
            "{}",
        ),
        (
            {ATTR_TASK: "564b9ac9-c53d-4638-9e7f-1cd96fe19baa"},
            "{}",
        ),
        (
            {ATTR_TASK: "alias_zahnseide_benutzen"},
            "{}",
        ),
        (
            {
                ATTR_RENAME: "new-task-name",
            },
            '{"text": "new-task-name"}',
        ),
        (
            {
                ATTR_DESCRIPTION: "new-task-description",
            },
            '{"notes": "new-task-description"}',
        ),
        (
            {
                ATTR_PRIORITY: "trivial",
            },
            '{"priority": 0.1}',
        ),
        (
            {
                ATTR_PRIORITY: "easy",
            },
            '{"priority": 1}',
        ),
        (
            {
                ATTR_PRIORITY: "medium",
            },
            '{"priority": 1.5}',
        ),
        (
            {
                ATTR_PRIORITY: "hard",
            },
            '{"priority": 2}',
        ),
        (
            {
                ATTR_START_DATE: "2024-10-14",
            },
            '{"startDate": "2024-10-14T00:00:00"}',
        ),
        (
            {
                ATTR_FREQUENCY: "daily",
            },
            '{"frequency": "daily"}',
        ),
        (
            {
                ATTR_FREQUENCY: "weekly",
            },
            '{"frequency": "weekly"}',
        ),
        (
            {
                ATTR_FREQUENCY: "monthly",
            },
            '{"frequency": "monthly"}',
        ),
        (
            {
                ATTR_FREQUENCY: "yearly",
            },
            '{"frequency": "yearly"}',
        ),
        (
            {
                ATTR_INTERVAL: 1,
            },
            '{"everyX": 1}',
        ),
        (
            {
                ATTR_REPEAT: ["su", "t", "th", "s"],
            },
            '{"repeat": {"m": false, "t": true, "w": false, "th": true, "f": false, "s": true, "su": true}}',
        ),
        (
            {
                ATTR_FREQUENCY: "monthly",
                ATTR_REPEAT_MONTHLY: "day_of_month",
            },
            '{"frequency": "monthly", "daysOfMonth": 6, "weeksOfMonth": []}',
        ),
        (
            {
                ATTR_FREQUENCY: "monthly",
                ATTR_REPEAT_MONTHLY: "day_of_week",
            },
            (
                '{"frequency": "monthly", "weeksOfMonth": 0, "repeat": {"m": false, "t": false, "w": '
                'false, "th": false, "f": false, "s": true, "su": false}, "daysOfMonth": []}'
            ),
        ),
        (
            {
                ATTR_STREAK: 100,
            },
            '{"streak": 100}',
        ),
        (
            {
                ATTR_REMINDER_TIME: ["20:00", "22:00"],
            },
            (
                '{"reminders": [{"id": "5d1935ff-80c8-443c-b2e9-733c66b44745", "startDate": "", "time": "2024-10-14T20:00:00+00:00"},'
                ' {"id": "5d1935ff-80c8-443c-b2e9-733c66b44745", "startDate": "", "time": "2024-10-14T22:00:00+00:00"},'
                ' {"id": "e2c62b7f-2e20-474b-a268-779252b25e8c", "startDate": "", "time": "2024-10-14T20:30:00+00:00"},'
                ' {"id": "4c472190-efba-4277-9d3e-ce7a9e1262ba", "startDate": "", "time": "2024-10-14T22:30:00+00:00"}]}'
            ),
        ),
        (
            {
                ATTR_REMOVE_REMINDER_TIME: ["22:30"],
            },
            '{"reminders": [{"id": "e2c62b7f-2e20-474b-a268-779252b25e8c", "startDate": "", "time": "2024-10-14T20:30:00+00:00"}]}',
        ),
        (
            {
                ATTR_CLEAR_REMINDER: True,
            },
            '{"reminders": []}',
        ),
    ],
    ids=[
        "match_task_by_name",
        "match_task_by_id",
        "match_task_by_alias",
        "rename",
        "description",
        "difficulty_trivial",
        "difficulty_easy",
        "difficulty_medium",
        "difficulty_hard",
        "start_date",
        "frequency_daily",
        "frequency_weekly",
        "frequency_monthly",
        "frequency_yearly",
        "interval",
        "repeat_days",
        "repeat_day_of_month",
        "repeat_day_of_week",
        "streak",
        "add_reminders",
        "remove_reminders",
        "clear_reminders",
    ],
)
async def test_update_daily(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_habitica: AiohttpClientMocker,
    service_data: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    """Test Habitica update_daily action."""

    mock_habitica.put(
        f"{DEFAULT_URL}/api/v3/tasks/564b9ac9-c53d-4638-9e7f-1cd96fe19baa",
        json={"success": True, "data": {}},
    )

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    await hass.services.async_call(
        DOMAIN,
        SERVICE_UPDATE_DAILY,
        service_data={
            ATTR_CONFIG_ENTRY: config_entry.entry_id,
            ATTR_TASK: "564b9ac9-c53d-4638-9e7f-1cd96fe19baa",
            **service_data,
        },
        return_response=True,
        blocking=True,
    )

    mock_call = mock_called_with(
        mock_habitica,
        "PUT",
        f"{DEFAULT_URL}/api/v3/tasks/564b9ac9-c53d-4638-9e7f-1cd96fe19baa",
    )
    assert mock_call
    assert mock_call[2] == expected
