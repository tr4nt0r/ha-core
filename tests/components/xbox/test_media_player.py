"""Test the Xbox media_player platform."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from pythonxbox.api.provider.smartglass.models import (
    SmartglassConsoleStatus,
    VolumeDirection,
)
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.media_player import (
    ATTR_MEDIA_VOLUME_MUTED,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    SERVICE_MEDIA_NEXT_TRACK,
    SERVICE_MEDIA_PAUSE,
    SERVICE_MEDIA_PLAY,
    SERVICE_MEDIA_PREVIOUS_TRACK,
    SERVICE_VOLUME_DOWN,
    SERVICE_VOLUME_MUTE,
    SERVICE_VOLUME_UP,
)
from homeassistant.components.xbox import DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from tests.common import (
    MockConfigEntry,
    async_load_json_object_fixture,
    snapshot_platform,
)
from tests.typing import MagicMock, WebSocketGenerator


@pytest.fixture(autouse=True)
def media_player_only() -> Generator[None]:
    """Enable only the media_player platform."""
    with patch(
        "homeassistant.components.xbox.PLATFORMS",
        [Platform.MEDIA_PLAYER],
    ):
        yield


@pytest.fixture(autouse=True)
def mock_token() -> Generator[MagicMock]:
    """Mock token generator."""
    with patch("secrets.token_hex", return_value="mock_token") as token:
        yield token


@pytest.mark.usefixtures("xbox_live_client")
async def test_media_players(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test setup of the Xbox media player platform."""

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    await snapshot_platform(hass, entity_registry, snapshot, config_entry.entry_id)


@pytest.mark.usefixtures("xbox_live_client")
async def test_browse_media(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Test async_browse_media."""

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": "media_player/browse_media",
            "entity_id": "media_player.xone",
        }
    )

    response = await client.receive_json()
    assert response["success"]

    assert response["result"] == snapshot(name="library")

    await client.send_json_auto_id(
        {
            "type": "media_player/browse_media",
            "entity_id": "media_player.xone",
            "media_content_id": "App",
            "media_content_type": "app",
        }
    )

    response = await client.receive_json()
    assert response["success"]

    assert response["result"] == snapshot(name="apps")

    await client.send_json_auto_id(
        {
            "type": "media_player/browse_media",
            "entity_id": "media_player.xone",
            "media_content_id": "Game",
            "media_content_type": "game",
        }
    )

    response = await client.receive_json()
    assert response["success"]

    assert response["result"] == snapshot(name="games")


async def test_turn_on(
    hass: HomeAssistant,
    xbox_live_client: AsyncMock,
    config_entry: MockConfigEntry,
) -> None:
    """Test media player turn on."""

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_TURN_ON,
        target={ATTR_ENTITY_ID: "media_player.xone"},
        blocking=True,
    )

    xbox_live_client.smartglass.wake_up.assert_called_once_with("HIJKLMN")


async def test_turn_off(
    hass: HomeAssistant,
    xbox_live_client: AsyncMock,
    config_entry: MockConfigEntry,
) -> None:
    """Test media player turn off."""

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_TURN_OFF,
        target={ATTR_ENTITY_ID: "media_player.xone"},
        blocking=True,
    )

    xbox_live_client.smartglass.turn_off.assert_called_once_with("HIJKLMN")


async def test_mute(
    hass: HomeAssistant,
    xbox_live_client: AsyncMock,
    config_entry: MockConfigEntry,
) -> None:
    """Test media player mute."""

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_MUTE,
        {ATTR_MEDIA_VOLUME_MUTED: True},
        target={ATTR_ENTITY_ID: "media_player.xone"},
        blocking=True,
    )

    xbox_live_client.smartglass.mute.assert_called_once_with("HIJKLMN")


async def test_unmute(
    hass: HomeAssistant,
    xbox_live_client: AsyncMock,
    config_entry: MockConfigEntry,
) -> None:
    """Test media player unmute."""

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_MUTE,
        {ATTR_MEDIA_VOLUME_MUTED: False},
        target={ATTR_ENTITY_ID: "media_player.xone"},
        blocking=True,
    )

    xbox_live_client.smartglass.unmute.assert_called_once_with("HIJKLMN")


@pytest.mark.parametrize(
    ("service", "payload"),
    [
        (SERVICE_VOLUME_UP, VolumeDirection.Up),
        (SERVICE_VOLUME_DOWN, VolumeDirection.Down),
    ],
)
async def test_volume(
    hass: HomeAssistant,
    xbox_live_client: AsyncMock,
    config_entry: MockConfigEntry,
    service: str,
    payload: VolumeDirection,
) -> None:
    """Test media player volume."""

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        service,
        target={ATTR_ENTITY_ID: "media_player.xone"},
        blocking=True,
    )

    xbox_live_client.smartglass.volume.assert_called_once_with("HIJKLMN", payload)


async def test_play(
    hass: HomeAssistant,
    xbox_live_client: AsyncMock,
    config_entry: MockConfigEntry,
) -> None:
    """Test media player play."""

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_MEDIA_PLAY,
        target={ATTR_ENTITY_ID: "media_player.xone"},
        blocking=True,
    )

    xbox_live_client.smartglass.play.assert_called_once_with("HIJKLMN")


async def test_pause(
    hass: HomeAssistant,
    xbox_live_client: AsyncMock,
    config_entry: MockConfigEntry,
) -> None:
    """Test media player pause."""

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_MEDIA_PAUSE,
        target={ATTR_ENTITY_ID: "media_player.xone"},
        blocking=True,
    )

    xbox_live_client.smartglass.pause.assert_called_once_with("HIJKLMN")


async def test_next_track(
    hass: HomeAssistant,
    xbox_live_client: AsyncMock,
    config_entry: MockConfigEntry,
) -> None:
    """Test media player next track."""

    xbox_live_client.smartglass.get_console_status.return_value = (
        SmartglassConsoleStatus(
            **await async_load_json_object_fixture(
                hass, "smartglass_console_status_playing.json", DOMAIN
            )  # type: ignore[reportArgumentType]
        )
    )

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_MEDIA_NEXT_TRACK,
        target={ATTR_ENTITY_ID: "media_player.xone"},
        blocking=True,
    )

    xbox_live_client.smartglass.next.assert_called_once_with("HIJKLMN")


async def test_previous_track(
    hass: HomeAssistant,
    xbox_live_client: AsyncMock,
    config_entry: MockConfigEntry,
) -> None:
    """Test media player previous track."""

    xbox_live_client.smartglass.get_console_status.return_value = (
        SmartglassConsoleStatus(
            **await async_load_json_object_fixture(
                hass, "smartglass_console_status_playing.json", DOMAIN
            )  # type: ignore[reportArgumentType]
        )
    )

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_MEDIA_PREVIOUS_TRACK,
        target={ATTR_ENTITY_ID: "media_player.xone"},
        blocking=True,
    )

    xbox_live_client.smartglass.previous.assert_called_once_with("HIJKLMN")
