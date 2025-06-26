"""Constants for the Playstation Network integration."""

from typing import Final

from psnawp_api.models.trophies import PlatformType

DOMAIN = "playstation_network"
CONF_NPSSO: Final = "npsso"

SUPPORTED_PLATFORMS = {
    PlatformType.PS5,
    PlatformType.PS4,
    PlatformType.PS3,
    PlatformType.PSPC,
}

NPSSO_LINK: Final = "https://ca.account.sony.com/api/v1/ssocookie"
PSN_LINK: Final = "https://playstation.com"

CONF_NP_COMMUNICATION_ID: Final = "np_communication_id"
CONF_PLATFORM: Final = "platform"
CONF_INCLUDE_TROPHIES: Final = "include_trophies"
