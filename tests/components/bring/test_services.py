"""Tests for services of Bring! integration."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

from bring_api import BringAuthException, BringParseException, BringRequestException
import pytest

from homeassistant.components.bring.const import (
    ATTR_CONFIG_ENTRY,
    ATTR_RECIPE_URL,
    DOMAIN,
    SERVICE_IMPORT_RECIPE,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from tests.common import MockConfigEntry


@pytest.fixture(autouse=True)
def services_only() -> Generator[None]:
    """Enable only services."""
    with patch(
        "homeassistant.components.bring.PLATFORMS",
        [],
    ):
        yield


async def test_import_recipe(
    hass: HomeAssistant,
    bring_config_entry: MockConfigEntry,
    mock_bring_client: AsyncMock,
) -> None:
    """Test import_recipe action."""

    bring_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(bring_config_entry.entry_id)
    await hass.async_block_till_done()

    assert bring_config_entry.state is ConfigEntryState.LOADED

    await hass.services.async_call(
        DOMAIN,
        SERVICE_IMPORT_RECIPE,
        service_data={
            ATTR_CONFIG_ENTRY: bring_config_entry.entry_id,
            ATTR_RECIPE_URL: "http://example.com",
        },
        return_response=True,
        blocking=True,
    )

    mock_bring_client.parse_recipe.assert_awaited_once_with("http://example.com")


@pytest.mark.parametrize(
    "exception",
    [BringRequestException, BringParseException, BringAuthException],
)
@pytest.mark.parametrize(
    "call_method",
    ["parse_recipe", "create_template"],
)
async def test_import_recipe_exception(
    hass: HomeAssistant,
    bring_config_entry: MockConfigEntry,
    mock_bring_client: AsyncMock,
    exception: Exception,
    call_method: str,
) -> None:
    """Test send bring push notification with exception."""

    bring_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(bring_config_entry.entry_id)
    await hass.async_block_till_done()

    assert bring_config_entry.state is ConfigEntryState.LOADED

    getattr(mock_bring_client, call_method).side_effect = exception
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_IMPORT_RECIPE,
            service_data={
                ATTR_CONFIG_ENTRY: bring_config_entry.entry_id,
                ATTR_RECIPE_URL: "http://example.com",
            },
            return_response=True,
            blocking=True,
        )


@pytest.mark.usefixtures("mock_bring_client")
async def test_get_config_entry(
    hass: HomeAssistant,
    bring_config_entry: MockConfigEntry,
) -> None:
    """Test config entry exceptions."""
    bring_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(bring_config_entry.entry_id)
    await hass.async_block_till_done()

    assert bring_config_entry.state is ConfigEntryState.LOADED

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_IMPORT_RECIPE,
            service_data={
                ATTR_CONFIG_ENTRY: "0000000000000000",
                ATTR_RECIPE_URL: "http://example.com",
            },
            return_response=True,
            blocking=True,
        )

    assert await hass.config_entries.async_unload(bring_config_entry.entry_id)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_IMPORT_RECIPE,
            service_data={
                ATTR_CONFIG_ENTRY: bring_config_entry.entry_id,
                ATTR_RECIPE_URL: "http://example.com",
            },
            return_response=True,
            blocking=True,
        )
