"""Interface to warp charger via http"""

import logging
import time
import requests
from requests.exceptions import HTTPError
from requests.structures import CaseInsensitiveDict

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

charger_keys = {
    'power':                        'charger_power',        
    'allowed_charging_current':     'charger_setpoint',        
    'charger_state':                'charger_status'        
}

charger_scale = {
    'charger_power':        1,        
    'charger_setpoint':     0.001,        
    'charger_status':       1        
}

URL_METER       = 'http://192.168.178.43/meter/values'
URL_CONTROLLER  = 'http://192.168.178.43/evse/state'
URL_AUTO_START  = 'http://192.168.178.43/evse/auto_start_charging'
URL_EXTERNAL    =  'http://192.168.178.43/evse/external_enabled'
URL_LIMIT = 'http://192.168.178.43/evse/external_current'
URL_STOP = 'http://192.168.178.43/evse/stop_charging'
URL_START = 'http://192.168.178.43/evse/start_charging'

HEADERS = CaseInsensitiveDict()
HEADERS["Content-Type"] = "application/json"

DATA_NULL = 'null'
MAX_CURRENT = 32
MIN_CURRENT = 6


def charger_write(url, data):
    """Write valus to URL."""
    logger.info("Write to charger %s %s", url, data)
    try:
        response = requests.put(url, headers=HEADERS, data=data, timeout=5)
        response.raise_for_status()
        return True
    except HTTPError as http_err:
        logger.error("HTTP error occurred: %s", http_err)
        return False
    except Exception as err:
        logger.error("Other error occurred: %s", err)
        return False


def charger_read(url):
    """Read jason values from a URL."""
    logger.info("Write to charger %s", url)
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except HTTPError as http_err:
        logger.error("HTTP error occurred: %s", http_err)
        return False
    except Exception as err:
        logger.error("Other error occurred: %s", err)
        return False


def init_charger():
    """Initialize the WARP charger for our needs."""
    if not charger_write(URL_AUTO_START, data = '{ "auto_start_charging": false }'):
        return False
    return charger_write(URL_EXTERNAL, data = '{ "enabled": true }')


def read_charger():
    """Read the charger."""
    #read 2 URLs
    response_meter = charger_read(URL_METER)
    response_controller = charger_read(URL_CONTROLLER)
    logger.info(str(response_controller))
    logger.info(str(response_meter))
    if not response_meter or not response_controller:
        return False
    response =  response_meter | response_controller

    #replace keys / filter
    ret_val = {}
    for key, value in response.items():
        for old_key, new_key in charger_keys.items():
            if key==old_key:
                ret_val[new_key] = int(value * charger_scale[new_key])
    return ret_val


def set_charger(setpoint):
    """Set charger max current."""
    setpoint = min(max(setpoint, MIN_CURRENT), MAX_CURRENT)
    data = '{"current":' + str(int(setpoint)) + '000}'
    return charger_write(URL_LIMIT, data)


def charger_on():
    """Turn Charger on."""
    return charger_write(URL_START, DATA_NULL)


def charger_off():
    "Turn off charger."
    return charger_write(URL_STOP, DATA_NULL)


def update_charger(power):
    """Set charger max power with some hystereses"""
    #calculate set point (current)
    setpoint =  max(min(round(power / 240), MAX_CURRENT), 0)
    logger.info("update_charger, setpoint %s", str(setpoint))

    if setpoint>=MIN_CURRENT:
        charger_on()
        set_charger(setpoint)

    #turn off a little late
    if setpoint<4:
        charger_off()


if __name__ == "__main__":
    logger.basicConfig(level=0)

    print("====Init charger=====")
    init_charger()
    time.sleep(5)

    print("====Test charger on=====")
    charger_on()
    time.sleep(5)
    print(read_charger())

    print("====Test set charger=====")
    set_charger(3)
    time.sleep(10)
    print(read_charger())

    print("====Test set charger=====")
    set_charger(31)
    time.sleep(10)
    print(read_charger())

    print("====Test set charger=====")
    set_charger(34)
    time.sleep(10)
    print(read_charger())

    print("====Test charger off=====")
    charger_off()
    time.sleep(10)
    print(read_charger())
