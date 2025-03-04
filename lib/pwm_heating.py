"""Set PWM """
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

MAX_SETPOINT = 220
MIN_SETPOINT = 10
POWER_2_PWM = 220/3000
TOPIC = "U_EL"


def get_heat_data(setpoint):
    """Set pwm heat over echo server"""
    if setpoint < MIN_SETPOINT:
        setpoint = 0
    setpoint = min(setpoint, MAX_SETPOINT)
    return {TOPIC: int(setpoint)}
