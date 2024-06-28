"""Tests for the Habitica To-dos."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

from habitipy.aio import HabitipyAsync
import pytest
from syrupy.assertion import SnapshotAssertion

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .conftest import TEST_DATA_PROFILE

from tests.common import MockConfigEntry, snapshot_platform


@pytest.fixture(autouse=True)
async def todo_only() -> AsyncGenerator[None, None]:
    """Enable only the todo platform."""
    with patch(
        "homeassistant.components.habitica.PLATFORMS",
        [Platform.TODO],
    ):
        yield


async def some_function_that_uses_habitica(habitipy: AsyncMock):
    """."""
    api = HabitipyAsync()
    assert await api.user.get(userFields="profile") == TEST_DATA_PROFILE


async def test_setup(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    habitipy: AsyncMock,
) -> None:
    """Test setup of the habitica to-do platform."""
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    await snapshot_platform(hass, entity_registry, snapshot, config_entry.entry_id)
