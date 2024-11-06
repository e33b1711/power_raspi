#!/usr/bin/python3
import socket
import sys
import argparse
import re
import signal
import logging
import time
import paho.mqtt.client as mqtt

# logging stuff
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# MQTT stuff
BROKER_ADDRESS = "localhost"
STATE_PREFIX = "ard_state/"
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
FIRST_RECONNECT_DELAY = 1
RECONNECT_RATE = 2
MAX_RECONNECT_COUNT = 12
MAX_RECONNECT_DELAY = 60

# ECHO server stuff
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ECHO_ADDRESS = ('raspberrypi.fritz.box', 8888)
BUFF_LEN = 256


def sock_send(message):
    """Send via socked with recover"""
    try:
        sock.send(message.encode())
    except socket.error:
        logger.error("Echo disconnected.")
        socket_connect()


def sock_recv():
    """Send via socked with recover"""
    try:
        return sock.recv(BUFF_LEN)
    except socket.error:
        logger.error("Echo disconnected.")
        socket_connect()
    return None


def socket_connect():
    """Connect to socket"""
    try:
        sock.connect(ECHO_ADDRESS)
    except socket.error as msg:
        logger.error("Execption while connecting. %s", str(msg))
        return False
    return True


def on_message(client, userdata, message):
    """Incoming mqtt message callback."""
    payload = str(message.payload.decode("utf-8"))
    logger.info("Incoming on MQTT: %s %s", message.topic, payload)
    topic = message.topic.split("/")
    if topic[0] == "ard_command":
        echo_message = f"!c!{topic[1]}!{payload}$\n"
        logger.info("Outgoing on ECHO: %s", echo_message.strip())
        sock_send(echo_message)


def publish_mqtt(key, payload):
    """Publish on MQTT."""
    logger.info("Outgoing on MQTT: %s %s", STATE_PREFIX + key, payload)
    client.publish(STATE_PREFIX + key, payload)


def signal_handler(sig, frame):
    """Clean up on exit"""
    sock.close()

    logger.info('Exit...')
    sys.exit(0)


def on_disconnect(client, userdata, rc):
    """MQTT recoverer."""
    logger.info("Disconnected with result code: %s", rc)
    reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
    while reconnect_count < MAX_RECONNECT_COUNT:
        logging.info("Reconnecting in %d seconds...", reconnect_delay)
        time.sleep(reconnect_delay)

        try:
            client.reconnect()
            logging.info("Reconnected successfully!")
            return
        except Exception as err:
            logger.error("%s. Reconnect failed. Retrying...", err)

        reconnect_delay *= RECONNECT_RATE
        reconnect_delay = min(reconnect_delay, MAX_RECONNECT_DELAY)
        reconnect_count += 1
    logging.info("Reconnect failed after %s attempts. Exiting...", reconnect_count)


def init():
    """Prepare everything"""
    # connect to ECHO server
    logger.info("connecting to %s port %s",
                str(ECHO_ADDRESS[0]), str(ECHO_ADDRESS[1]))
    if not socket_connect():
        logger.error("No inital ECHO connection. Exit..")
        sys.exit(-1)

    # init mqtt
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    client.connect(BROKER_ADDRESS)
    client.loop_start()
    client.subscribe([("ard_state/#", 1), ("ard_command/#", 1)])

    # gracefull strg+c
    signal.signal(signal.SIGINT, signal_handler)

    logger.info("Init done.")


def get_message(mess_buff):
    """get complete message from echo."""
    messages = []
    buff = sock_recv()
    if buff is None:
        mess_buff = ""
        return messages, mess_buff
    mess_buff += buff.decode('utf8')

    while "$" in mess_buff:
        message, mess_buff = re.split("\n|$", mess_buff,maxsplit=1)
        message = message.strip()
        logger.debug("stripped message: %s",message)
        if message != "":
            messages.append(message)
    logger.debug("returning messages: %s", str(messages))
    logger.debug("remaining buff: %s", mess_buff)
    return messages, mess_buff


def send_message(messages):
    """Send ECHO message via MQTT"""
    for message in messages:
        logger.debug("Send message: >>%s<<", message)
        logger.debug("message.count('!') %i", message.count('!'))
        if not message.count('!') == 3:
            logger.warning("Defective ECHO message: >>%s<<", message)
            continue
        logger.info("Incoming on ECHO: %s", message)
        logger.debug("message.split(!): %s", str(message.split("!")))
        _, message_type, topic, payload = message.replace('$','').split("!")

        if message_type == "s":
            publish_mqtt(topic, payload)
        else:
            logger.debug("Message not type s: %s", message)


def main():
    """Relay between ECHO server and mqtt"""
    init()
    mess_buff = ""
    while True:
        messages, mess_buff = get_message(mess_buff)
        send_message(messages)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument( '-log',
                     '--loglevel',
                     default='warning',
                     help='Provide logging level. Example --loglevel debug, default=warning' )
    args = parser.parse_args()
    logger.setLevel(level=args.loglevel.upper() )
    main()
