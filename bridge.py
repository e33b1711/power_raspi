"""TCP relay ser"""
import socket
import argparse
import logging
import signal
import re
import time
from lib.mqtt import mqtt_publish_ard_state, mqtt_init, mqtt_stop
from lib.get_ip import get_ip
from lib.git_revision import get_git_rev


# global stuff
end_threads = False
HEART_RATE = 60
last_haert_beat = 0
git_rev = get_git_rev()

# tcp stuff
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# logging stuff
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# MQTT stuff
BROKER = "ironmaiden"
TOPICS = ["ard_command/#"]


def get_message(mess_buff):
    """get complete message from echo."""
    parts =  re.split(r'\$', mess_buff)
    return [part.strip() + "$" for part in parts if part.strip()]


def send_mqtt(messages):
    """Send ECHO message via MQTT"""
    for message in messages:
        logger.debug("Send message: >>%s<<", message)
        logger.debug("message.count('!') %i", message.count('!'))
        if not message.count('!') == 3:
            logger.warning("Defective ECHO message: >>%s<<", message)
            continue
        logger.debug("Incoming on ECHO: %s", message)
        logger.debug("message.split(!): %s", str(message.split("!")))
        _, message_type, topic, payload = message.replace('$', '').split("!")

        if message_type == "s":
            mqtt_publish_ard_state({topic: payload})
        else:
            logger.debug("Message not type s: %s", message)


def init_socket(ip_address, port):
    """Open the socket"""
    client.settimeout(0.2)
    server_address = (ip_address, port)
    client.connect(server_address)
    logger.info("CLient listening on %s , %i", str(ip_address), port)


def on_message(mqtt_client, userdata, message):
    """Incoming mqtt message callback."""
    payload = str(message.payload.decode("utf-8"))
    logger.debug("Incoming on MQTT: %s %s", message.topic, payload)
    topic = message.topic.split("/")
    if topic[0] == "ard_command":
        echo_message = f"!c!{topic[1]}!{payload}$\n"
        logger.info("Outgoing on ECHO: %s", echo_message.strip())
        client.send(echo_message.encode())


def signal_handler(sig, frame):
    """Clean up on exit"""
    logger.info('Closing down.')
    global end_threads
    end_threads = True


def beat_heart():
    """Send git rev message all n minutes."""
    global last_haert_beat
    if last_haert_beat + HEART_RATE < time.time():
        logger.info("Sending heart beat: %s", git_rev)
        mqtt_publish_ard_state({"bridge_service": git_rev})
        last_haert_beat = time.time()


def main_loop():
    """read socket. relay to mqtt."""
    logger.debug("Enter main loop")
    while not end_threads:
        beat_heart()
        try:
            data = client.recv(1024)
        except socket.timeout:
            pass
        else:
            if not data:
                break
            message = data.decode('utf-8')
            logger.debug("Received message: %s", message)
            send_mqtt(get_message(message))


def main(broker):
    """Main function"""

    get_ip(exit_on_fail=True)
    mqtt_init(TOPICS, [on_message], broker=broker, reconnect=False)
    init_socket("127.0.0.1", 8889)
    signal.signal(signal.SIGINT, signal_handler)
    main_loop()
    mqtt_stop()



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-log',
                        '--loglevel',
                        default='warning',
                        help='Provide logging level. Example --loglevel debug, default=warning')
    parser.add_argument('-b',
                        '--broker',
                        default=BROKER,
                        help='MQTT Broker')
    args = parser.parse_args()
    logger.setLevel(level=args.loglevel.upper())
    main(args.broker)
