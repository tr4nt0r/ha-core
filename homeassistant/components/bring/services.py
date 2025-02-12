"""Actions for Bring! integration."""

import logging

from bring_api import (
    BringAuthException,
    BringParseException,
    BringRequestException,
    TemplateType,
)
import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_EMAIL
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.selector import ConfigEntrySelector

from .const import ATTR_CONFIG_ENTRY, ATTR_RECIPE_URL, DOMAIN, SERVICE_IMPORT_RECIPE
from .coordinator import BringConfigEntry

_LOGGER = logging.getLogger(__name__)

SERVICE_IMPORT_RECIPE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY): ConfigEntrySelector({"integration": DOMAIN}),
        vol.Required(ATTR_RECIPE_URL): vol.Url(),
    }
)


def get_config_entry(hass: HomeAssistant, entry_id: str) -> BringConfigEntry:
    """Return config entry or raise if not found or not loaded."""
    if not (entry := hass.config_entries.async_get_entry(entry_id)):
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="entry_not_found",
        )
    if entry.state is not ConfigEntryState.LOADED:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="entry_not_loaded",
        )
    return entry


def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Bring! integration."""

    async def import_recipe(call: ServiceCall) -> ServiceResponse:
        """Import recipe action."""

        entry = get_config_entry(hass, call.data[ATTR_CONFIG_ENTRY])
        coordinator = entry.runtime_data

        try:
            recipe = await coordinator.bring.parse_recipe(call.data[ATTR_RECIPE_URL])
            return (
                await coordinator.bring.create_template(recipe, TemplateType.RECIPE)
            ).to_dict(omit_none=True)
        except (BringRequestException, BringParseException) as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="recipe_import_failed",
            ) from e
        except BringAuthException as e:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="setup_authentication_exception",
                translation_placeholders={CONF_EMAIL: coordinator.bring.mail},
            ) from e

    hass.services.async_register(
        DOMAIN,
        SERVICE_IMPORT_RECIPE,
        import_recipe,
        schema=SERVICE_IMPORT_RECIPE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
