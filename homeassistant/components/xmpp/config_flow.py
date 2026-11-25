"""Config flow for the XMPP integration."""

import logging
from typing import Any, override

import probatio
from slixmpp import ClientXMPP
from slixmpp.xmlstream.xmlstream import NotConnectedError

from homeassistant import data_entry_flow
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryData,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PLATFORM,
    CONF_PORT,
    CONF_RECIPIENT,
    CONF_RESOURCE,
    CONF_ROOM,
    CONF_SENDER,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.field_visibility import ConditionOperator
from homeassistant.helpers.instance_id import async_get as async_get_instance_id
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import CONF_TLS, CONF_VERIFY, DEFAULT_RESOURCE, DOMAIN, XMPPSubentryType

_LOGGER = logging.getLogger(__name__)

SECTION_CONNECTION = "connection"

STEP_USER_DATA_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_SENDER): cv.string,
        probatio.Required(probatio.Secret(CONF_PASSWORD)): cv.string,
        probatio.Required(SECTION_CONNECTION): data_entry_flow.section(
            probatio.Schema(
                {
                    probatio.Optional(CONF_HOST): probatio.Hostname(),
                    data_entry_flow.Required(
                        CONF_PORT,
                        default=5222,
                        visible={"field": "host", "operator": ConditionOperator.EXISTS},
                    ): probatio.Port(),
                    probatio.Required(CONF_TLS, default=True): cv.boolean,
                    probatio.Required(CONF_VERIFY, default=True): cv.boolean,
                },
            ),
            {"collapsed": True},
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate that the XMPP credentials can establish a session."""
    xmpp = await hass.async_add_executor_job(
        ClientXMPP, data[CONF_SENDER], data[CONF_PASSWORD]
    )

    xmpp.loop = hass.loop
    xmpp.enable_starttls = data.get(CONF_TLS, True)
    xmpp.enable_direct_tls = data.get(CONF_TLS, True)
    xmpp.enable_plaintext = not data.get(CONF_TLS)
    xmpp.plugin["feature_mechanisms"].unencrypted_scram = not data.get(CONF_TLS)

    login_result = xmpp.connect(data.get(CONF_HOST), data.get(CONF_PORT))

    async def session_started(_: Any) -> None:
        if not login_result.done():
            await xmpp.disconnect()
            login_result.set_result(None)

    def authentication_failed(_: Any) -> None:
        if not login_result.done():
            login_result.set_exception(InvalidAuth)

    xmpp.add_event_handler("session_start", session_started)
    xmpp.add_event_handler("failed_all_auth", authentication_failed)

    if not data[CONF_VERIFY]:
        xmpp.add_event_handler("ssl_invalid_cert", lambda _: None)

    try:
        await login_result
    except InvalidAuth:
        raise
    except TimeoutError:
        raise
    except (NotConnectedError, ConnectionError, OSError) as err:
        raise CannotConnect from err


class XMPPConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for XMPP."""

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._async_abort_entries_match({CONF_SENDER: user_input[CONF_SENDER]})
            try:
                await validate_input(
                    self.hass, {**user_input, **user_input[SECTION_CONNECTION]}
                )
            except TimeoutError:
                errors["base"] = "timeout_connect"
            except CannotConnect:
                _LOGGER.debug("Full exception:", exc_info=True)
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_SENDER],
                    data={**user_input.pop(SECTION_CONNECTION), **user_input},
                    options={
                        CONF_RESOURCE: (
                            f"{DEFAULT_RESOURCE}."
                            f"{await async_get_instance_id(self.hass)}"
                        )
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                data_schema=STEP_USER_DATA_SCHEMA, suggested_values=user_input
            ),
            errors=errors,
        )

    async def async_step_import(self, import_info: dict[str, Any]) -> ConfigFlowResult:
        """Import config from yaml."""
        errors: dict[str, str] = {}
        self._async_abort_entries_match(
            {
                CONF_SENDER: import_info[CONF_SENDER],
                CONF_NAME: import_info.get(CONF_NAME),
            }
        )

        try:
            await validate_input(self.hass, import_info)
        except TimeoutError:
            errors["base"] = "timeout_connect"
        except CannotConnect:
            _LOGGER.debug("Full exception:", exc_info=True)
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            title = import_info.get(CONF_NAME) or import_info[CONF_SENDER]
            room = import_info.pop(CONF_ROOM, None)
            recipients = import_info.pop(CONF_RECIPIENT, [])
            subentries = (
                [
                    ConfigSubentryData(
                        subentry_type=XMPPSubentryType.GROUPCHAT,
                        title=room,
                        unique_id=room,
                        data={},
                    )
                ]
                if room
                else [
                    ConfigSubentryData(
                        subentry_type=XMPPSubentryType.CHAT,
                        title=recipient,
                        unique_id=recipient,
                        data={},
                    )
                    for recipient in recipients
                ]
            )
            import_info.pop(CONF_PLATFORM, None)
            resource = import_info.pop(CONF_RESOURCE, DEFAULT_RESOURCE)
            return self.async_create_entry(
                title=title,
                data=import_info,
                options={CONF_RESOURCE: resource},
                subentries=subentries,
            )

        return self.async_abort(reason=errors["base"])

    @classmethod
    @callback
    @override
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return subentries supported by this integration."""
        return {
            XMPPSubentryType.CHAT: ChatSubentryFlowHandler,
            XMPPSubentryType.GROUPCHAT: ChatSubentryFlowHandler,
        }


class ChatSubentryFlowHandler(ConfigSubentryFlow):
    """Handle subentry flow for adding a recipient."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """User flow to add a new recipient."""

        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_RECIPIENT],
                data={},
                unique_id=user_input[CONF_RECIPIENT],
            )

        return self.async_show_form(
            step_id="user",
            data_schema=probatio.Schema(
                {
                    probatio.Required(CONF_RECIPIENT): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.EMAIL),
                    ),
                }
            ),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
