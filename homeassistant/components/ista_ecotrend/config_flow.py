"""Config flow for ista EcoTrend integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import TYPE_CHECKING, Any

from pyecotrend_ista import KeycloakError, LoginError, PyEcotrendIsta, ServerError
import voluptuous as vol

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_EMAIL, CONF_NAME, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from . import IstaConfigEntry
from .const import CONF_CODE, CONF_OTP, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.EMAIL,
                autocomplete="email",
            )
        ),
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.PASSWORD,
                autocomplete="current-password",
            )
        ),
        vol.Optional(CONF_CODE): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.TEXT,
                autocomplete="one-time-code",
            )
        ),
    }
)

OPTIONS_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_OTP): EntitySelector(
            EntitySelectorConfig(domain=SENSOR_DOMAIN, integration="otp"),
        )
    }
)

OPTIONS_PLACEHOLDER = {"url": "/config/integrations/dashboard/add?domain=otp"}


class IstaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ista EcoTrend."""

    reauth_entry: IstaConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            ista = PyEcotrendIsta(
                email=user_input[CONF_EMAIL],
                password=user_input[CONF_PASSWORD],
                totp=user_input[CONF_CODE],
            )
            try:
                await self.hass.async_add_executor_job(ista.login)
                info = ista.get_account()
            except ServerError:
                errors["base"] = "cannot_connect"
            except (LoginError, KeycloakError):
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                if TYPE_CHECKING:
                    assert info
                title = f"{info["firstName"]} {info["lastName"]}".strip()
                await self.async_set_unique_id(info["activeConsumptionUnit"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=title or "ista EcoTrend", data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                data_schema=STEP_USER_DATA_SCHEMA, suggested_values=user_input
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Perform reauth upon an API authentication error."""
        self.reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Dialog that informs the user that reauth is required."""
        errors: dict[str, str] = {}
        if TYPE_CHECKING:
            assert self.reauth_entry

        if user_input is not None:
            ista = PyEcotrendIsta(
                email=user_input[CONF_EMAIL],
                password=user_input[CONF_PASSWORD],
                totp=user_input[CONF_CODE],
            )
            try:
                await self.hass.async_add_executor_job(ista.login)
            except ServerError:
                errors["base"] = "cannot_connect"
            except (LoginError, KeycloakError):
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    self.reauth_entry, data=user_input
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self.add_suggested_values_to_schema(
                data_schema=STEP_USER_DATA_SCHEMA,
                suggested_values={
                    CONF_EMAIL: user_input[CONF_EMAIL]
                    if user_input is not None
                    else self.reauth_entry.data[CONF_EMAIL]
                },
            ),
            description_placeholders={
                CONF_NAME: self.reauth_entry.title,
                CONF_EMAIL: self.reauth_entry.data[CONF_EMAIL],
            },
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(OptionsFlow):
    """Handle an option flow for ista EcoTrend."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_DATA_SCHEMA, self.config_entry.options
            ),
            description_placeholders=OPTIONS_PLACEHOLDER,
        )
