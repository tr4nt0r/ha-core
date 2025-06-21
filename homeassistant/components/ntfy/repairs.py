"""Repairs for ntfy integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol

from homeassistant import data_entry_flow
from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


class ProtectedTopicRepairFlow(RepairsFlow):
    """Deactivate and unsubscribe a protected topic."""

    def __init__(
        self,
        data: dict[str, str | int | float | None] | None,
    ) -> None:
        """Initialize."""
        super().__init__()

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the first step of a fix flow."""

        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the confirm step of a fix flow."""
        if user_input is not None:
            if TYPE_CHECKING:
                assert self.data
                assert isinstance(self.data["entity_id"], str)
            entity_registry = er.async_get(self.hass)
            entity_entry = entity_registry.async_get(self.data["entity_id"])
            if entity_entry:
                entity_registry.async_update_entity(
                    entity_entry.entity_id,
                    disabled_by=er.RegistryEntryDisabler.USER,
                )
            return self.async_create_entry(data={})

        return self.async_show_form(step_id="confirm", data_schema=vol.Schema({}))


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create flow."""

    return (
        ProtectedTopicRepairFlow(data)
        if issue_id == "topic_protected"
        else ConfirmRepairFlow()
    )
