"""Common fixtures for the XMPP tests."""

from collections.abc import Callable, Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant.common import MockConfigEntry

from homeassistant.components.xmpp.const import (
    CONF_TLS,
    CONF_VERIFY,
    DEFAULT_RESOURCE,
    DOMAIN,
    XMPPSubentryType,
)
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.const import CONF_PASSWORD, CONF_RESOURCE, CONF_SENDER


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "homeassistant.components.xmpp.async_setup_entry", return_value=None
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture(name="config_entry")
def mock_config_entry() -> MockConfigEntry:
    """Mock smtp configuration entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="jabber@example.com",
        data={
            CONF_SENDER: "test@example.com",
            CONF_PASSWORD: "test-password",
            CONF_TLS: True,
            CONF_VERIFY: True,
        },
        options={CONF_RESOURCE: f"{DEFAULT_RESOURCE}.instance_id"},
        entry_id="123456789",
        subentries_data=[
            ConfigSubentryData(
                data={},
                subentry_type=XMPPSubentryType.CHAT,
                title="jabber@example.com",
                unique_id="jabber@example.com",
            )
        ],
    )


@pytest.fixture
def mock_instance_id() -> Generator[None]:
    """Mock instance id."""

    with patch(
        "homeassistant.components.xmpp.config_flow.async_get_instance_id",
        return_value="test_instance",
    ):
        yield


@pytest.fixture
def mock_slixmpp() -> Generator[AsyncMock]:
    """Mock slixmpp."""

    with patch(
        "homeassistant.components.xmpp.config_flow.ClientXMPP", autospec=True
    ) as mock_client:
        client = mock_client.return_value
        client.handlers: dict[str, Callable[[Any], Any]] = {}

        def add_event_handler(event: str, handler: Callable[[Any], Any]) -> None:
            """Add a mock event handler."""
            client.handlers[event] = handler

        client.add_event_handler.side_effect = add_event_handler
        client.plugin = MagicMock()

        client.connect = AsyncMock()

        yield client
