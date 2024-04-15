"""Pinecil Library."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bleak.backends.device import BLEDevice

LIVE_DATA_POLL_INTERVAL = 10
SETTINGS_POLL_INTERVAL = 60


class Pinecil:
    """Pinecil class."""

    data: dict[str, Any] = {}

    def __init__(self, ble_device: BLEDevice) -> None:
        """Initialize class."""

    def poll_needed(self, seconds_since_last_poll: float | None) -> bool:
        """Return if device needs polling."""
        if (
            seconds_since_last_poll is not None
            and seconds_since_last_poll < LIVE_DATA_POLL_INTERVAL
        ):
            return False
        return True
