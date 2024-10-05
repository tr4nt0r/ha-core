"""Constants for the habitica integration."""

from homeassistant.const import CONF_PATH

CONF_API_USER = "api_user"

DEFAULT_URL = "https://habitica.com"
ASSETS_URL = "https://habitica-assets.s3.amazonaws.com/mobileApp/images/"
DOMAIN = "habitica"

# service constants
SERVICE_API_CALL = "api_call"
ATTR_PATH = CONF_PATH
ATTR_ARGS = "args"

# event constants
EVENT_API_CALL_SUCCESS = f"{DOMAIN}_{SERVICE_API_CALL}_success"
ATTR_DATA = "data"

MANUFACTURER = "HabitRPG, Inc."
NAME = "Habitica"

UNIT_TASKS = "tasks"

ATTR_CONFIG_ENTRY = "config_entry"
ATTR_SKILL = "skill"
ATTR_TASK = "task"
ATTR_TYPE = "type"
ATTR_PRIORITY = "priority"
ATTR_TAG = "tag"
ATTR_KEYWORD = "keyword"

SERVICE_CAST_SKILL = "cast_skill"
SERVICE_GET_TASKS = "get_tasks"

PRIORITIES = {"trivial": 0.1, "easy": 1, "medium": 1.5, "hard": 2}

DEVELOPER_ID = "4c4ca53f-c059-4ffa-966e-9d29dd405daf"
