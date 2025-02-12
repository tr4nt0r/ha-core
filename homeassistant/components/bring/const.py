"""Constants for the Bring! integration."""

from typing import Final

DOMAIN = "bring"

ATTR_SENDER: Final = "sender"
ATTR_ITEM_NAME: Final = "item"
ATTR_NOTIFICATION_TYPE: Final = "message"
ATTR_RECIPE_URL: Final = "recipe_url"
ATTR_CONFIG_ENTRY: Final = "config_entry_id"

SERVICE_PUSH_NOTIFICATION = "send_message"
SERVICE_IMPORT_RECIPE = "import_recipe"
