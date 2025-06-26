"""Config flow for the PlayStation Network integration."""

from collections.abc import Mapping
import logging
from typing import TYPE_CHECKING, Any

from psnawp_api.core.psnawp_exceptions import (
    PSNAWPAuthenticationError,
    PSNAWPError,
    PSNAWPInvalidTokenError,
    PSNAWPNotFoundError,
)
from psnawp_api.models.trophies import TrophyTitle
from psnawp_api.models.user import User
from psnawp_api.utils.misc import parse_npsso_token
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
)

from .const import (
    CONF_INCLUDE_TROPHIES,
    CONF_NP_COMMUNICATION_ID,
    CONF_NPSSO,
    CONF_PLATFORM,
    DOMAIN,
    NPSSO_LINK,
    PSN_LINK,
)
from .coordinator import PlaystationNetworkConfigEntry
from .helpers import PlaystationNetwork, fmt_game_title

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required(CONF_NPSSO): str})
STEP_SUBENTRY_GAME_DATA_SCHEMA = {vol.Required(CONF_INCLUDE_TROPHIES): bool}


class PlaystationNetworkConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Playstation Network."""

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return subentries supported by this integration."""
        return {"game": GameSubentryFlowHandler}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        npsso: str | None = None
        if user_input is not None:
            try:
                npsso = parse_npsso_token(user_input[CONF_NPSSO])
            except PSNAWPInvalidTokenError:
                errors["base"] = "invalid_account"
            else:
                psn = PlaystationNetwork(self.hass, npsso)
                try:
                    user: User = await psn.get_user()
                except PSNAWPAuthenticationError:
                    errors["base"] = "invalid_auth"
                except PSNAWPNotFoundError:
                    errors["base"] = "invalid_account"
                except PSNAWPError:
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("Unexpected exception")
                    errors["base"] = "unknown"
                else:
                    await self.async_set_unique_id(user.account_id)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=user.online_id,
                        data={CONF_NPSSO: npsso},
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "npsso_link": NPSSO_LINK,
                "psn_link": PSN_LINK,
            },
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Perform reauth upon an API authentication error."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauthentication dialog."""
        errors: dict[str, str] = {}

        entry = self._get_reauth_entry()

        if user_input is not None:
            try:
                npsso = parse_npsso_token(user_input[CONF_NPSSO])
                psn = PlaystationNetwork(self.hass, npsso)
                user: User = await psn.get_user()
            except PSNAWPAuthenticationError:
                errors["base"] = "invalid_auth"
            except (PSNAWPNotFoundError, PSNAWPInvalidTokenError):
                errors["base"] = "invalid_account"
            except PSNAWPError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user.account_id)
                self._abort_if_unique_id_mismatch(
                    description_placeholders={
                        "wrong_account": user.online_id,
                        CONF_NAME: entry.title,
                    }
                )

                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={CONF_NPSSO: npsso},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self.add_suggested_values_to_schema(
                data_schema=STEP_USER_DATA_SCHEMA, suggested_values=user_input
            ),
            errors=errors,
            description_placeholders={
                "npsso_link": NPSSO_LINK,
                "psn_link": PSN_LINK,
            },
        )


class GameSubentryFlowHandler(ConfigSubentryFlow):
    """Handle subentry flow for adding and modifying a game."""

    titles: list[TrophyTitle] | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """User flow to add a game."""
        errors: dict[str, str] = {}
        config_entry: PlaystationNetworkConfigEntry = self._get_entry()
        exist = [subentry.unique_id for subentry in config_entry.subentries.values()]

        def get_titles() -> list[TrophyTitle]:
            if TYPE_CHECKING:
                assert config_entry.runtime_data.psn.client
            return list(config_entry.runtime_data.psn.client.trophy_titles())

        if not self.titles:
            self.titles = await self.hass.async_add_executor_job(get_titles)

        if user_input is not None:
            title = next(
                title
                for title in self.titles
                if title.np_communication_id == user_input[CONF_NP_COMMUNICATION_ID]
            )

            return self.async_create_entry(
                title=f"{fmt_game_title(title)} ({next(iter(title.title_platform)).name.replace('_', ' ')})",
                data={
                    **user_input,
                    CONF_NAME: fmt_game_title(title),
                    CONF_PLATFORM: next(iter(title.title_platform)).name,
                },
                unique_id=user_input[CONF_NP_COMMUNICATION_ID],
            )

        options = [
            SelectOptionDict(
                value=title.np_communication_id,
                label=f"{fmt_game_title(title)} ({next(iter(title.title_platform)).name.replace('_', ' ')})",
            )
            for title in self.titles
            if title.np_communication_id and title.np_communication_id not in exist
        ]

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_NP_COMMUNICATION_ID): SelectSelector(
                            SelectSelectorConfig(sort=True, options=options)
                        )
                    }
                ).extend(STEP_SUBENTRY_GAME_DATA_SCHEMA),
                user_input,
            ),
            errors=errors,
        )
