"""Tests for the XMPP integration."""

from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant.common import MockConfigEntry

from homeassistant.components.notify import DOMAIN as NOTIFY_DOMAIN
from homeassistant.components.xmpp.const import (
    CONF_TLS,
    CONF_VERIFY,
    DEFAULT_RESOURCE,
    DOMAIN,
    XMPPSubentryType,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PLATFORM,
    CONF_RECIPIENT,
    CONF_RESOURCE,
    CONF_ROOM,
    CONF_SENDER,
)
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN, HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component


@pytest.mark.usefixtures("mock_slixmpp")
async def test_entry_setup_unload(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Test integration setup and unload."""

    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    assert hass.services.has_service(NOTIFY_DOMAIN, "jabber_example_com")

    assert await hass.config_entries.async_unload(config_entry.entry_id)

    assert config_entry.state is ConfigEntryState.NOT_LOADED

    assert not hass.services.has_service(NOTIFY_DOMAIN, "jabber_example_com")


@pytest.mark.usefixtures("mock_slixmpp")
async def test_import(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test yaml import."""

    await async_setup_component(
        hass,
        NOTIFY_DOMAIN,
        {
            NOTIFY_DOMAIN: [
                {
                    CONF_PLATFORM: DOMAIN,
                    CONF_SENDER: "jabber@example.com",
                    CONF_NAME: "jabber@example.com",
                    CONF_PASSWORD: "password",
                    CONF_RECIPIENT: ["jabber1@example.com", "jabber2@example.com"],
                    CONF_RESOURCE: f"{DEFAULT_RESOURCE}-12345",
                    CONF_TLS: True,
                    CONF_VERIFY: True,
                },
                {
                    CONF_PLATFORM: DOMAIN,
                    CONF_NAME: "chatroom",
                    CONF_SENDER: "jabber@example.com",
                    CONF_PASSWORD: "password",
                    CONF_RECIPIENT: ["jabber@example.com"],
                    CONF_ROOM: "jabber@conference.example.com",
                    CONF_TLS: True,
                    CONF_VERIFY: True,
                },
            ]
        },
    )
    await hass.async_block_till_done()

    assert mock_setup_entry.call_count == 2
    assert len(entries := hass.config_entries.async_entries(DOMAIN)) == 2

    assert len(entries[0].subentries) == 2

    assert entries[0].title == "jabber@example.com"
    assert entries[0].data == {
        CONF_SENDER: "jabber@example.com",
        CONF_NAME: "jabber@example.com",
        CONF_PASSWORD: "password",
        CONF_TLS: True,
        CONF_VERIFY: True,
    }
    assert entries[0].options == {CONF_RESOURCE: f"{DEFAULT_RESOURCE}-12345"}
    subentries = list(entries[0].subentries.values())
    assert subentries[0].unique_id == "jabber1@example.com"
    assert subentries[0].subentry_type == XMPPSubentryType.CHAT
    assert subentries[1].unique_id == "jabber2@example.com"
    assert subentries[1].subentry_type == XMPPSubentryType.CHAT

    assert len(entries[1].subentries) == 1
    assert entries[1].title == "chatroom"
    assert entries[1].data == {
        CONF_SENDER: "jabber@example.com",
        CONF_NAME: "chatroom",
        CONF_PASSWORD: "password",
        CONF_TLS: True,
        CONF_VERIFY: True,
    }
    assert entries[1].options == {CONF_RESOURCE: DEFAULT_RESOURCE}
    subentries = list(entries[1].subentries.values())
    assert subentries[0].unique_id == "jabber@conference.example.com"
    assert subentries[0].subentry_type == XMPPSubentryType.GROUPCHAT

    assert issue_registry.async_get_issue(
        domain=HOMEASSISTANT_DOMAIN,
        issue_id=f"deprecated_yaml_{DOMAIN}",
    )


@pytest.mark.usefixtures("mock_slixmpp")
async def test_import_already_configured(
    hass: HomeAssistant,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test yaml import aborts if already configured."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="jabber@example.com",
        data={
            CONF_NAME: "jabber@example.com",
            CONF_SENDER: "jabber@example.com",
            CONF_PASSWORD: "password",
            CONF_TLS: True,
            CONF_VERIFY: True,
        },
        options={
            CONF_RESOURCE: f"{DEFAULT_RESOURCE}-12345",
        },
        entry_id="123456789",
    )

    config_entry.add_to_hass(hass)

    await async_setup_component(
        hass,
        NOTIFY_DOMAIN,
        {
            NOTIFY_DOMAIN: [
                {
                    CONF_PLATFORM: DOMAIN,
                    CONF_SENDER: "jabber@example.com",
                    CONF_NAME: "jabber@example.com",
                    CONF_PASSWORD: "password",
                    CONF_RECIPIENT: ["jabber@example.com"],
                    CONF_RESOURCE: f"{DEFAULT_RESOURCE}-12345",
                    CONF_TLS: True,
                    CONF_VERIFY: True,
                },
            ]
        },
    )

    await hass.async_block_till_done()

    assert len(hass.config_entries.async_entries(DOMAIN)) == 1

    assert issue_registry.async_get_issue(
        domain=HOMEASSISTANT_DOMAIN,
        issue_id=f"deprecated_yaml_{DOMAIN}",
    )


async def test_import_errors(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    issue_registry: ir.IssueRegistry,
    mock_slixmpp: AsyncMock,
) -> None:
    """Test yaml triggers import flow, aborts with errors, and creates error issue."""
    mock_slixmpp.connect.side_effect = ValueError

    await async_setup_component(
        hass,
        NOTIFY_DOMAIN,
        {
            NOTIFY_DOMAIN: [
                {
                    CONF_PLATFORM: DOMAIN,
                    CONF_SENDER: "jabber@example.com",
                    CONF_NAME: "jabber",
                    CONF_PASSWORD: "password",
                    CONF_RECIPIENT: ["jabber@example.com"],
                    CONF_RESOURCE: f"{DEFAULT_RESOURCE}-12345",
                    CONF_TLS: True,
                    CONF_VERIFY: True,
                },
            ]
        },
    )
    await hass.async_block_till_done()

    assert len(mock_setup_entry.mock_calls) == 0
    assert len(hass.config_entries.async_entries(DOMAIN)) == 0

    assert not issue_registry.async_get_issue(
        domain=HOMEASSISTANT_DOMAIN,
        issue_id=f"deprecated_yaml_{DOMAIN}",
    )
    assert issue_registry.async_get_issue(
        domain=DOMAIN,
        issue_id=("deprecated_yaml_import_issue_error_jabber_jabber@example.com"),
    )
