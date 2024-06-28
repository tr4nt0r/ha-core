"""Tests for the habitica component."""

from collections.abc import Generator
import logging
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.components.habitica.const import DEFAULT_URL, DOMAIN

from tests.common import MockConfigEntry

_LOGGER = logging.getLogger(__name__)

TEST_USER_NAME = "test_user"

USER_INPUT = {
    "url": DEFAULT_URL,
    "api_user": "test-api-user",
    "api_key": "test-api-key",
}

TEST_DATA_PROFILE = {
    "data": {
        "api_user": "test-api-user",
        "profile": {"name": TEST_USER_NAME},
        "stats": {
            "class": "warrior",
            "con": 1,
            "exp": 2,
            "gp": 3,
            "hp": 4,
            "int": 5,
            "lvl": 6,
            "maxHealth": 7,
            "maxMP": 8,
            "mp": 9,
            "per": 10,
            "points": 11,
            "str": 12,
            "toNextLevel": 13,
        },
    }
}


@pytest.fixture(autouse=True)
def disable_plumbum():
    """Disable plumbum in tests as it can cause the test suite to fail.

    plumbum can leave behind PlumbumTimeoutThreads
    """
    with patch("plumbum.local"), patch("plumbum.colors"):
        yield


@pytest.fixture(name="config_entry")
def mock_config_entry() -> MockConfigEntry:
    """Mock Habitica configuration entry."""
    return MockConfigEntry(
        domain=DOMAIN, title="test_user", data=USER_INPUT, entry_id="ENTRY_ID"
    )


@pytest.fixture(name="habitipy")
def mock_habitipy() -> Generator[AsyncMock, None, None]:
    """Mock habitipy."""
    with patch(
        "homeassistant.components.habitica.HabitipyAsync",
        new_callable=AsyncMock(),
    ) as mock_obj:
        client = mock_obj

        client.user.return_value = AsyncMock()

        yield mock_obj
