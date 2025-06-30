"""Helper methods for common PlayStation Network integration operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from psnawp_api import PSNAWP
from psnawp_api.models.client import Client
from psnawp_api.models.trophies import PlatformType, TrophySummary
from psnawp_api.models.user import User
from pyrate_limiter import Duration, Rate

from homeassistant.core import HomeAssistant

from .const import SUPPORTED_PLATFORMS

LEGACY_PLATFORMS = {PlatformType.PS3, PlatformType.PS4}


@dataclass(kw_only=True, frozen=True)
class SessionData:
    """Dataclass representing console session data."""

    platform: PlatformType
    title_id: str | None = None
    title_name: str | None = None
    format: PlatformType | None = None
    media_image_url: str | None = None
    status: str


@dataclass(kw_only=True, frozen=True)
class PlaystationNetworkData:
    """Dataclass representing data retrieved from the Playstation Network api."""

    presence: dict[str, Any]
    username: str
    account_id: str
    availability: str = "unavailable"
    active_sessions: dict[PlatformType, SessionData]
    registered_platforms: set[PlatformType]
    trophy_summary: TrophySummary
    profile: dict[str, Any]


class PlaystationNetwork:
    """Helper Class to return playstation network data in an easy to use structure."""

    def __init__(self, hass: HomeAssistant, npsso: str) -> None:
        """Initialize the class with the npsso token."""
        rate = Rate(300, Duration.MINUTE * 15)
        self.psn = PSNAWP(npsso, rate_limit=rate)
        self.client: Client
        self.hass = hass
        self.user: User

    def _setup(self) -> None:
        """Initialize the PSN Client."""

        self.user = self.psn.user(online_id="me")
        self.client = self.psn.me()

    async def async_setup(self) -> bool:
        """Get the user object from the PlayStation Network."""
        await self.hass.async_add_executor_job(self._setup)
        return True

    def retrieve_psn_data(
        self,
    ) -> tuple[
        set[PlatformType],
        dict[str, Any],
        TrophySummary,
        dict[str, Any],
        dict[str, Any] | None,
    ]:
        """Bundle api calls to retrieve data from the PlayStation Network."""

        return (
            (
                registered_platforms := {
                    PlatformType(device["deviceType"])
                    for device in self.client.get_account_devices()
                }
                & SUPPORTED_PLATFORMS
            ),
            self.user.get_presence(),
            self.client.trophy_summary(),
            self.user.profile(),
            (
                self.client.get_profile_legacy()
                if LEGACY_PLATFORMS & registered_platforms
                else None
            ),
        )

    async def get_data(self) -> PlaystationNetworkData:
        """Get title data from the PlayStation Network."""
        active_sessions: dict[PlatformType, SessionData] = {}

        (
            registered_platforms,
            presence,
            trophy_summary,
            profile,
            legacy_profile,
        ) = await self.hass.async_add_executor_job(self.retrieve_psn_data)

        if (
            platform := PlatformType(
                presence["basicPresence"]["primaryPlatformInfo"]["platform"]
            )
        ) in SUPPORTED_PLATFORMS:
            game_title_info = (
                info[0]
                if (info := presence["basicPresence"].get("gameTitleInfoList"))
                else {}
            )

            active_sessions[platform] = SessionData(
                platform=platform,
                title_id=game_title_info.get("npTitleId"),
                title_name=game_title_info.get("titleName"),
                format=PlatformType(game_title_info.get("format")),
                media_image_url=game_title_info.get(
                    "conceptIconUrl", game_title_info.get("npTitleIconUrl")
                ),
                status=presence["basicPresence"]["primaryPlatformInfo"]["onlineStatus"],
            )

        if legacy_profile:
            lgcy_presence = legacy_profile["profile"].get("presences", [])
            if (
                game_title_info := lgcy_presence[0] if lgcy_presence else {}
            ) and game_title_info["onlineStatus"] == "online":
                platform = PlatformType(game_title_info["platform"])

                if platform is PlatformType.PS4:
                    media_image_url = game_title_info.get("npTitleIconUrl")
                elif platform is PlatformType.PS3 and game_title_info.get("npTitleId"):
                    media_image_url = self.psn.game_title(
                        game_title_info["npTitleId"],
                        platform=PlatformType.PS3,
                        account_id="me",
                        np_communication_id="",
                    ).get_title_icon_url()
                else:
                    media_image_url = None

                active_sessions[platform] = SessionData(
                    platform=platform,
                    title_id=game_title_info.get("npTitleId"),
                    title_name=game_title_info.get("titleName"),
                    format=platform,
                    media_image_url=media_image_url,
                    status=game_title_info["onlineStatus"],
                )
        return PlaystationNetworkData(
            presence=presence,
            username=self.user.online_id,
            account_id=self.user.account_id,
            availability=presence["basicPresence"]["availability"],
            active_sessions=active_sessions,
            registered_platforms=registered_platforms,
            trophy_summary=trophy_summary,
            profile=profile,
        )
