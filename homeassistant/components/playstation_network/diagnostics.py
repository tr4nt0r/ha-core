"""Diagnostics support for Playstation Network."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import PlaystationNetworkConfigEntry
from .coordinator import PlaystationNetworkCoordinator

TO_REDACT: dict[str, str] = {}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: PlaystationNetworkConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: PlaystationNetworkCoordinator = entry.runtime_data.coordinator
    return async_redact_data(coordinator.data, TO_REDACT)
