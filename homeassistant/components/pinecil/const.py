"""Constants for the Pinecil integration."""

from enum import StrEnum

DOMAIN = "pinecil"

MANUFACTURER = "Pine64"
MODEL = "Pinecil V2"

OHM = "Ω"

MAX_TEMP: int = 450
MIN_TEMP: int = 10
MIN_BOOST_TEMP: int = 250


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
    SLEEP_TEMP = "sleep_temperature"
    SLEEP_TIMEOUT = "sleep_timeout"
    QC_MAX_VOLTAGE = "qc_max_voltage"
    PD_TIMEOUT = "pd_timeout"
    BOOST_TEMP = "boost_temp"
    SHUTDOWN_TIMEOUT = "shutdown_timeout"
    DISPLAY_BRIGHTNESS = "display_brightness"
