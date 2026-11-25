"""Constants for the Jabber (XMPP) integration."""

from enum import StrEnum

DOMAIN = "xmpp"

DEFAULT_RESOURCE = "home-assistant"

CONF_TLS = "tls"
CONF_VERIFY = "verify"


class XMPPSubentryType(StrEnum):
    """Subentry type."""

    CHAT = "chat"
    GROUPCHAT = "groupchat"
