"""Test the XMPP config flow."""

from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant.common import MockConfigEntry
from slixmpp.xmlstream.xmlstream import NotConnectedError

from homeassistant.components.xmpp.config_flow import SECTION_CONNECTION, InvalidAuth
from homeassistant.components.xmpp.const import (
    CONF_TLS,
    CONF_VERIFY,
    DEFAULT_RESOURCE,
    DOMAIN,
    XMPPSubentryType,
)
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_RECIPIENT,
    CONF_RESOURCE,
    CONF_SENDER,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType


@pytest.mark.usefixtures("mock_slixmpp", "mock_instance_id")
async def test_form(hass: HomeAssistant, mock_setup_entry: AsyncMock) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        "xmpp", context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SENDER: "jabber@example.com",
            CONF_PASSWORD: "test-password",
            SECTION_CONNECTION: {
                CONF_TLS: True,
                CONF_VERIFY: True,
            },
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "jabber@example.com"
    assert result["data"] == {
        CONF_SENDER: "jabber@example.com",
        CONF_PASSWORD: "test-password",
        CONF_TLS: True,
        CONF_VERIFY: True,
    }
    assert result["options"] == {CONF_RESOURCE: f"{DEFAULT_RESOURCE}.test_instance"}
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("exception", "error_msg"),
    [
        (InvalidAuth, "invalid_auth"),
        (NotConnectedError, "cannot_connect"),
        (ConnectionError, "cannot_connect"),
        (OSError, "cannot_connect"),
        (TimeoutError, "timeout_connect"),
        (ValueError, "unknown"),
    ],
)
@pytest.mark.usefixtures("mock_instance_id")
async def test_form_errors(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    mock_slixmpp: AsyncMock,
    exception: Exception,
    error_msg: str,
) -> None:
    """Test we handle invalid authentication."""
    result = await hass.config_entries.flow.async_init(
        "xmpp", context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    mock_slixmpp.connect.side_effect = exception

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_SENDER: "jabber@example.com",
            CONF_PASSWORD: "test-password",
            SECTION_CONNECTION: {
                CONF_TLS: True,
                CONF_VERIFY: True,
            },
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error_msg}
    assert mock_setup_entry.call_count == 0

    mock_slixmpp.connect.side_effect = None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_SENDER: "jabber@example.com",
            CONF_PASSWORD: "test-password",
            SECTION_CONNECTION: {
                CONF_TLS: True,
                CONF_VERIFY: True,
            },
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "jabber@example.com"
    assert result["data"] == {
        CONF_SENDER: "jabber@example.com",
        CONF_PASSWORD: "test-password",
        CONF_TLS: True,
        CONF_VERIFY: True,
    }
    assert result["options"] == {CONF_RESOURCE: f"{DEFAULT_RESOURCE}.test_instance"}
    assert mock_setup_entry.call_count == 1


@pytest.mark.parametrize(
    "subentry_type",
    [
        XMPPSubentryType.CHAT,
        XMPPSubentryType.GROUPCHAT,
    ],
)
@pytest.mark.usefixtures("mock_slixmpp", "mock_instance_id")
async def test_form_subentry(
    hass: HomeAssistant, config_entry: MockConfigEntry, subentry_type: XMPPSubentryType
) -> None:
    """Test subentry flow form."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="jabber@example.com",
        data={
            CONF_SENDER: "jabber@example.com",
            CONF_PASSWORD: "test-password",
            CONF_TLS: True,
            CONF_VERIFY: True,
        },
        options={CONF_RESOURCE: f"{DEFAULT_RESOURCE}.instance_id"},
        entry_id="123456789",
    )

    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    result = await hass.config_entries.subentries.async_init(
        (config_entry.entry_id, subentry_type),
        context={"source": SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], user_input={CONF_RECIPIENT: "jabber@example.com"}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["unique_id"] == "jabber@example.com"
    assert result["handler"] == (config_entry.entry_id, subentry_type)

    assert len(config_entry.subentries) == 1
