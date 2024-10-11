"""Actions for the Habitica integration."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from aiohttp import ClientResponseError
import voluptuous as vol

from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import ConfigEntrySelector

from .const import ATTR_CONFIG_ENTRY, ATTR_SKILL, ATTR_TASK, DOMAIN, SERVICE_CAST_SKILL
from .types import HabiticaConfigEntry

SERVICE_CAST_SKILL_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY): ConfigEntrySelector(),
        vol.Required(ATTR_SKILL): cv.string,
        vol.Optional(ATTR_TASK): cv.string,
    }
)


def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Habitica integration."""

    async def cast_skill(call: ServiceCall) -> ServiceResponse:
        """Skill action."""
        entry: HabiticaConfigEntry | None
        if not (
            entry := hass.config_entries.async_get_entry(call.data[ATTR_CONFIG_ENTRY])
        ):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="entry_not_found",
            )
        coordinator = entry.runtime_data
        skill = {
            "pickpocket": {"spellId": "pickPocket", "cost": "10 MP"},
            "backstab": {"spellId": "backStab", "cost": "15 MP"},
            "smash": {"spellId": "smash", "cost": "10 MP"},
            "fireball": {"spellId": "fireball", "cost": "10 MP"},
        }
        try:
            task_id = next(
                task["id"]
                for task in coordinator.data.tasks
                if call.data[ATTR_TASK] in (task["id"], task.get("alias"))
                or call.data[ATTR_TASK] == task["text"]
            )
        except StopIteration as e:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="task_not_found",
                translation_placeholders={"task": f"'{call.data[ATTR_TASK]}'"},
            ) from e

        try:
            response: dict[str, Any] = await coordinator.api.user.class_.cast[
                skill[call.data[ATTR_SKILL]]["spellId"]
            ].post(targetId=task_id)
        except ClientResponseError as e:
            if e.status == HTTPStatus.TOO_MANY_REQUESTS:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="setup_rate_limit_exception",
                ) from e
            if e.status == HTTPStatus.UNAUTHORIZED:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="not_enough_mana",
                    translation_placeholders={
                        "cost": skill[call.data[ATTR_SKILL]]["cost"],
                        "mana": f"{int(coordinator.data.user.get("stats", {}).get("mp", 0))} MP",
                    },
                ) from e
            if e.status == HTTPStatus.NOT_FOUND:
                # could also be task not found, but the task is looked up
                # before the request, so most likely wrong skill selected
                # or the skill hasn't been unlocked yet.
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="skill_not_found",
                    translation_placeholders={"skill": call.data[ATTR_SKILL]},
                ) from e
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="service_call_exception",
            ) from e
        else:
            await coordinator.async_request_refresh()
            return response

    hass.services.async_register(
        DOMAIN,
        SERVICE_CAST_SKILL,
        cast_skill,
        schema=SERVICE_CAST_SKILL_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
