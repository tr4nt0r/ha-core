"""Test the habitica config flow."""

from unittest.mock import AsyncMock, patch

from habiticalib import BadRequestError, HabiticaErrorResponse, NotAuthorizedError
from multidict import CIMultiDict, CIMultiDictProxy
import pytest

from homeassistant import config_entries
from homeassistant.components.habitica.const import CONF_API_USER, DEFAULT_URL, DOMAIN
from homeassistant.const import (
    CONF_API_KEY,
    CONF_PASSWORD,
    CONF_URL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

MOCK_DATA_LOGIN_STEP = {
    CONF_USERNAME: "test-email@example.com",
    CONF_PASSWORD: "test-password",
}
MOCK_DATA_ADVANCED_STEP = {
    CONF_API_USER: "5f359083-ef78-4af0-985a-0b2c6d05797c",
    CONF_API_KEY: "94ffa5cb-43f3-4715-8592-584a97422b67",
    CONF_URL: DEFAULT_URL,
    CONF_VERIFY_SSL: True,
}


@pytest.mark.usefixtures("mock_habitica")
async def test_form_login(hass: HomeAssistant) -> None:
    """Test we get the login form."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.MENU
    assert "login" in result["menu_options"]
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "login"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}
    assert result["step_id"] == "login"

    with (
        patch(
            "homeassistant.components.habitica.async_setup", return_value=True
        ) as mock_setup,
        patch(
            "homeassistant.components.habitica.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=MOCK_DATA_LOGIN_STEP,
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "test-username"
    assert result["data"] == {
        **MOCK_DATA_ADVANCED_STEP,
        CONF_USERNAME: "test-username",
    }
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("raise_error", "text_error"),
    [
        (
            BadRequestError(
                HabiticaErrorResponse(success=False, error="", message=""),
                CIMultiDictProxy(CIMultiDict()),
            ),
            "cannot_connect",
        ),
        (
            NotAuthorizedError(
                HabiticaErrorResponse(success=False, error="", message=""),
                CIMultiDictProxy(CIMultiDict()),
            ),
            "invalid_auth",
        ),
        (IndexError(), "unknown"),
    ],
    ids=["cannot_connect", "invalid_auth", "unknown"],
)
async def test_form_login_errors(
    hass: HomeAssistant, raise_error, text_error, mock_habiticalib: AsyncMock
) -> None:
    """Test we handle invalid credentials error."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "login"}
    )

    mock_habiticalib.login.side_effect = raise_error

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_DATA_LOGIN_STEP,
    )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": text_error}


@pytest.mark.usefixtures("mock_habitica")
async def test_form_advanced(hass: HomeAssistant) -> None:
    """Test we get the form."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.MENU
    assert "advanced" in result["menu_options"]
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "advanced"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}
    assert result["step_id"] == "advanced"

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "advanced"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "homeassistant.components.habitica.async_setup", return_value=True
        ) as mock_setup,
        patch(
            "homeassistant.components.habitica.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=MOCK_DATA_ADVANCED_STEP,
        )
        await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "test-username"
    assert result2["data"] == {
        **MOCK_DATA_ADVANCED_STEP,
        CONF_USERNAME: "test-username",
    }
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("raise_error", "text_error"),
    [
        (
            BadRequestError(
                HabiticaErrorResponse(success=False, error="", message=""),
                CIMultiDictProxy(CIMultiDict()),
            ),
            "cannot_connect",
        ),
        (
            NotAuthorizedError(
                HabiticaErrorResponse(success=False, error="", message=""),
                CIMultiDictProxy(CIMultiDict()),
            ),
            "invalid_auth",
        ),
        (IndexError(), "unknown"),
    ],
    ids=["cannot_connect", "invalid_auth", "unknown"],
)
async def test_form_advanced_errors(
    hass: HomeAssistant,
    raise_error,
    text_error,
    mock_habiticalib: AsyncMock,
) -> None:
    """Test we handle invalid credentials error."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "advanced"}
    )

    mock_habiticalib.get_user.side_effect = raise_error

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_DATA_ADVANCED_STEP,
    )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": text_error}
