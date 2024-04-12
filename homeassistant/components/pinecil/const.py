"""Constants for the Pinecil integration."""

from enum import StrEnum

DOMAIN = "pinecil"

MANUFACTURER = "Pine64"
MODEL = "Pinecil V2"

UPDATE_SECONDS = 1
DEVICE_TIMEOUT = 5

OHM = "Ω"


class PinecilEntity(StrEnum):
    """Pinecil Entities."""

    LIVE_TEMP = "live_temperature"
    SETPOINT_TEMP = "setpoint_temperature"
    DC_VOLTAGE = "voltage"
    HANDLETEMP = "handle_temperature"
    PWMLEVEL = "power_pwm_level"
    POWER_SRC = "power_source"
    TIP_RESISTANCE = "tip_resistance"
    UPTIME = "uptime"
    MOVEMENT_TIME = "movement_time"
    MAX_TIP_TEMP_ABILITY = "max_tip_temp_ability"
    TIP_VOLTAGE = "tip_voltage"
    HALL_SENSOR = "hall_sensor"
    OPERATING_MODE = "operating_mode"
    ESTIMATED_POWER = "estimated_power"


POWER_SOURCES = ["dc", "qc", "pd vbus", "pd"]
OPERATING_MODES = ["idle", "soldering", "boost", "sleeping", "settings", "debug"]
