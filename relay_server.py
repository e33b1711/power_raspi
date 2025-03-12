"""TCP relay ser"""
import socket
import threading
import argparse
import logging
import signal
import re
import time
from lib.mqtt import mqtt_publish, mqtt_init, mqtt_stop
from lib.get_ip import get_ip
from lib.git_revision import get_git_rev


# global stuff
end_threads = False
HEART_RATE = 60*5
last_haert_beat = 0
git_rev = get_git_rev()

# tcp stuff
client_socks: list = []
client_threads: list = []
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# logging stuff
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# MQTT stuff
BROKER = "ironmaiden"
STATE_PREFIX = "ard_state/"
TOPICS = ["ard_command/#"]


def filter_types(messages):
    """Filter out state messages."""
    messages_out = ""
    for message in messages:
        if "!s!" not in message:
            messages_out += message + "\n"
            logger.debug("Going through: %s", message)
        else:
            logger.debug("Filtered out: %s", message)

    return messages_out.encode()


def handle_client(client_socket):
    """Client thread function"""

    while not end_threads:
        try:
            data = client_socket.recv(1024)
        except socket.timeout:
            pass
        else:
            if not data:
                break

            message = data.decode('utf-8')
            logger.debug("Received message: %s", message)

            # send via mqtt
            messages = get_message(message)
            send_mqtt(messages)

            # relay to the others
            broadcast(filter_types(messages), client_socket)

    logger.info("Closing client thread.")


def broadcast(message, connection=None):
    """Relay message to all clients"""
    if message == "":
        return
    for client in client_socks:
        logger.debug("Relay: %s", str(client))
        if client != connection:
            try:
                client.send(message)
            except Exception as e:
                logger.error("Caught Exception: %s", str(e))
                client.close()
                remove(client)
        else:
            logger.debug("Not relay: %s", str(client))



def get_message(mess_buff):
    """get complete message from echo."""
    messages = []
    while "$" in mess_buff:
        message, mess_buff = re.split("\n|$", mess_buff, maxsplit=1)
        message = message.strip()
        logger.debug("stripped message: %s", message)
        if message != "":
            messages.append(message)
    logger.debug("returning messages: %s", str(messages))
    logger.debug("remaining buff: %s", mess_buff)
    return messages


def send_mqtt(messages):
    """Send ECHO message via MQTT"""
    for message in messages:
        logger.debug("Send message: >>%s<<", message)
        logger.debug("message.count('!') %i", message.count('!'))
        if not message.count('!') == 3:
            logger.warning("Defective ECHO message: >>%s<<", message)
            continue
        logger.info("Incoming on ECHO: %s", message)
        logger.debug("message.split(!): %s", str(message.split("!")))
        _, message_type, topic, payload = message.replace('$', '').split("!")

        if message_type == "s":
            mqtt_publish({topic: payload})
        else:
            logger.debug("Message not type s: %s", message)


def remove(client):
    """Remove client from list"""
    if client in client_socks:
        client_socks.remove(client)


def init_socket(ip_address, port):
    """Open the socket"""
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.settimeout(0.2)
    server_socket.bind((ip_address, port))
    server_socket.listen(5)
    logger.info("Server listening on %s , %i", str(ip_address), port)


def on_message(client, userdata, message):
    """Incoming mqtt message callback."""
    payload = str(message.payload.decode("utf-8"))
    logger.info("Incoming on MQTT: %s %s", message.topic, payload)
    topic = message.topic.split("/")
    if topic[0] == "ard_command":
        echo_message = f"!c!{topic[1]}!{payload}$\n"
        logger.info("Outgoing on ECHO: %s", echo_message.strip())
        broadcast(echo_message.encode())


def signal_handler(sig, frame):
    """Clean up on exit"""
    logger.info('Closing down.')
    global end_threads
    end_threads = True


def shut_down():
    """End Threads. Close sockets."""

    logger.info('waiting for threads to close')
    for thread in client_threads:
        thread.join()
    logger.info('All threads closed. Good bye!')

    logger.info('Closing sockets...')
    server_socket.close()
    for sock in client_socks:
        sock.close()
    logger.info('Closing sockets done.')


def beat_heart():
    """Send git rev message all n minutes."""
    global last_haert_beat
    if last_haert_beat + HEART_RATE < time.time():
        logger.debug("Sending heart beat: %s", git_rev)
        mqtt_publish({STATE_PREFIX + "relay_service": git_rev})
        last_haert_beat = time.time()


def main_loop():
    """Accept incomming connections. Start threads to handel them."""

    while not end_threads:
        beat_heart()

        try:
            client_socket, client_address = server_socket.accept()
            client_socket.settimeout(0.2)
        except socket.timeout:
            pass
        else:
            logger.info("Accepted connection from %s", str(client_address))
            client_handler = threading.Thread(
                target=handle_client, args=(client_socket,))
            client_handler.start()
            client_socks.append(client_socket)
            client_threads.append(client_handler)


def main(broker):
    """Main function"""

    primary_ip = get_ip(exit_on_fail=True)
    mqtt_init(TOPICS, [on_message], broker=broker)
    init_socket(primary_ip, 8888)
    signal.signal(signal.SIGINT, signal_handler)

    main_loop()

    mqtt_stop()
    shut_down()


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
