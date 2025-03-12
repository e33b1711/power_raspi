"""Controls PV charger and electric heater, interfaces to openhab via mqtt"""
import time
import signal
import argparse
import sys
import logging
import math

from lib.victron import read_victron, MAX_BATT_IN_POWER
from lib.warp_charger import charger_on, charger_off, read_charger
from lib.warp_charger import update_charger, init_charger, set_charger
from lib.mqtt import mqtt_publish, mqtt_init, COMMAND_TOPICS, STATE_PREFIX, mqtt_stop, mqtt_publish_ard_command
from lib.pwm_heating import get_heat_data, POWER_2_PWM, MAX_SETPOINT, MIN_SETPOINT
from lib.git_revision import get_git_rev

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

INTERVAL = 5
ON_VALS = ['ON', '1']
OFF_VALS = ['OFF', '0']

HEART_RATE = 60*5
last_haert_beat = 0
git_rev = get_git_rev()

all_data = {
    # collected data
    'grid_power': -1,
    'solar_power': -1,
    'battery_power': -1,
    'loads_power': -1,
    'criticial_loads_power': -1,
    'ess_setpoint':             0,
    'victron_status': -1,
    'state_of_charge': -1,
    'charger_power': -1,
    'charger_setpoint': -1,
    'charger_status': -1,
    'heat_connected': -1,
    # own data
    'heat_conneted':            0,
    'victron_connected':        0,
    'charger_connected':        0,
    'delta_power':              None,
    'heat_setpoint':            0,
    'solar_power_mean':         None,
    'solar2heat':               "OFF",
    'solar2car':                "OFF",
    'car_connected':            "OFF",
    'charging':                 "OFF",
    'last_update':              None
}


def signal_handler(sig, frame):
    """Handle exit gracefully"""

    # disconnected / turned off
    data = {}
    data['solar2heat'] = 0
    data['solar2car'] = 0
    data['charger_connected'] = 0
    data['victron_connected'] = 0
    data['heat_connected'] = 0

    # turn off charger
    charger_off()
    mqtt_publish(get_charger())

    # publish mqtt control states
    mqtt_publish(data)
    mqtt_stop()

    logger.info("Goodbye")
    sys.exit(0)


def callback_set_flag(client, userdata, message):
    """Get mqtt messages"""
    payload = str(message.payload.decode("utf-8"))
    logger.info("mqtt calback set_flag %s %s", message.topic, str(payload))
    for key in all_data:
        if key in message.topic:
            all_data[key] = payload


def call_back_set_charger(client, userdata, message):
    """Get mqtt messages"""
    payload_val = int(message.payload.decode("utf-8"))
    if all_data['solar2car'] not in ON_VALS:
        logger.info("mqtt calback set charger: %s", str(payload_val))
        set_charger(round(payload_val))
        mqtt_publish(get_charger())
    else:
        logger.info(
            "mqtt calback set charger: %s [blocked by solar2car]", str(payload_val))


def call_back_switch_charger(client, userdata, message):
    """Get mqtt messages"""
    payload_val = message.payload.decode("utf-8")
    if all_data['solar2car'] not in ON_VALS:
        logger.info("mqtt calback switch charger: %s", str(payload_val))
        if payload_val in OFF_VALS:
            charger_off()
        if payload_val in ON_VALS:
            charger_on()
        mqtt_publish(get_charger())
    else:
        logger.info(
            "mqtt calback switch charger: %s [blocked by solar2car]", str(payload_val))


def calc_aux_power():
    """Calc some auxilary power values"""
    # calculate delta power (give battery in power priority)
    if all_data['state_of_charge'] > 90:
        batt_in_power = MAX_BATT_IN_POWER/10 * \
            (100-int(all_data['state_of_charge']))
    else:
        batt_in_power = MAX_BATT_IN_POWER
    all_data['delta_power'] = -1*all_data['grid_power'] - \
        batt_in_power + all_data['battery_power']

    # calculate mean solar power
    if all_data['solar_power_mean']:
        all_data['solar_power_mean'] += 0.01 * \
            (all_data['solar_power']-all_data['solar_power_mean'])
    else:
        all_data['solar_power_mean'] = all_data['solar_power']
    # set to 0 eventually
    if all_data['solar_power_mean'] < 10 and all_data['solar_power'] == 0:
        all_data['solar_power_mean'] = 0.0


def charger_control():
    """Charger control algorithm"""
    # translate status to flags
    match all_data['charger_status']:
        case 1 | 2:
            all_data['car_connected'] = 1
            all_data['charging'] = "OFF"
        case 3:
            all_data['car_connected'] = 1
            all_data['charging'] = "ON"
        case _:
            all_data['car_connected'] = 0
            all_data['charging'] = "OFF"

    # pv power controll
    if all_data['solar2car'] in ON_VALS:
        charger_update = all_data['solar_power_mean']*0.9
        update_charger(charger_update)
        logger.info("Update charger: %s", str(charger_update))


def cut_off(data, lower):
    """Set to Zero on lower bound."""
    if data < lower:
        return 0
    return data


def heat_control():
    """Heat control algorithm"""
    if all_data['solar2heat'] in ON_VALS:
        last_sp = all_data['heat_setpoint']
        increment = math.ceil(all_data['delta_power'] * POWER_2_PWM * 0.5)

        # start late at 30
        if all_data['heat_setpoint'] == 0:
            all_data['heat_setpoint'] = increment
        else:
            all_data['heat_setpoint'] += increment

        # limit
        all_data['heat_setpoint'] = min(
            all_data['heat_setpoint'], MAX_SETPOINT)
        # cut off
        all_data['heat_setpoint'] = cut_off(
            all_data['heat_setpoint'], MIN_SETPOINT)

        logger.info("New heat setpoint: %s", str(all_data['heat_setpoint']))

        # write 0 only once
        if not (last_sp == 0 and all_data['heat_setpoint'] == 0):
            mqtt_publish_ard_command(get_heat_data(all_data['heat_setpoint']))


def get_victron():
    """read victron => update all data"""
    result = read_victron()
    if not result:
        all_data['victron_connected'] = 0
        return
    all_data['victron_connected'] = 1
    for key, val in result.items():
        all_data[key] = val


def get_charger():
    """read charger =>  update all data"""
    result = read_charger()
    ret_dict = {}
    if not result:
        all_data['charger_connected'] = 0
        logger.error("Cant reach chrager")
        return None
    all_data['charger_connected'] = 1
    for key, val in result.items():
        logger.debug("read charger: %s %s", key, str(val))
        all_data[key] = val
        ret_dict[key] = val
    return ret_dict


def kill_some_time():
    """Call me to kill the reamining interval."""
    if not all_data['last_update']:
        # init
        all_data['last_update'] = time.time()
    else:
        # wait
        while time.time() < all_data['last_update'] + INTERVAL:
            time.sleep(0.1)
        all_data['last_update'] += 5
    logger.debug("End of loop. %s", str(all_data['last_update']))


def beat_heart():
    """Send git rev message all n minutes."""
    global last_haert_beat
    if last_haert_beat + HEART_RATE < time.time():
        logger.debug("Sending heart beat: %s", git_rev)
        mqtt_publish({"power_service": git_rev})
        last_haert_beat = time.time()


def main():
    """Main loop and init"""

    signal.signal(signal.SIGINT, signal_handler)
    mqtt_init(COMMAND_TOPICS, [callback_set_flag, callback_set_flag, call_back_set_charger,
                               call_back_switch_charger], broker="127.0.0.1")
    init_charger()

    logger.info("Init done.")

    while True:
        beat_heart()
        kill_some_time()
        get_victron()
        get_charger()
        calc_aux_power()
        charger_control()
        heat_control()
        mqtt_publish(all_data)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-log',
                        '--loglevel',
                        default='warning',
                        help='Provide logging level. Example --loglevel debug, default=warning')
    args = parser.parse_args()
    logger.setLevel(level=args.loglevel.upper())
    main()
