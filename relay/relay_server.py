"""TCP relay ser"""
import socket
import threading
import sys
import logging
import signal
import re
import time
import paho.mqtt.client as mqtt


# tcp stuff
client_socks: list = []
client_threads: list = []
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
end_threads = False

# logging stuff
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# MQTT stuff
BROKER_ADDRESS = "ironmaiden"
STATE_PREFIX = "ard_state/"
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
FIRST_RECONNECT_DELAY = 1
RECONNECT_RATE = 2
MAX_RECONNECT_COUNT = 12
MAX_RECONNECT_DELAY = 60


def get_ip():
    """Get primary IP adddress of this host"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(('10.254.254.254', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


def handle_client(client_socket):
    """Client thread function"""

    while not end_threads:
        try:
            data = client_socket.recv(1024)
        except socket.timeout:
            pass
        except:
            raise
        else:
            if not data:
                break

            message = data.decode('utf-8')
            logger.debug("Received message: %s", message)

            # send via mqtt
            messages = get_message(message)
            send_mqtt(messages)

            # dont relay state messages
            logger.debug("message count: " + str(message.count('!s!')))
            if message.count('!s!') == 0:
                logger.debug("tcp brodcasting: " + message)
                broadcast(data, client_socket)

    logger.info("Closing client thread.")


def broadcast(message, connection=None):
    """Relay message to all clients"""

    for client in client_socks:
        if client != connection:
            try:
                client.send(message)
            except:
                client.close()
                remove(client)


def get_message(mess_buff):
    """get complete message from echo."""

    messages = []
    while "$" in mess_buff:
        message, mess_buff = re.split("\n|$", mess_buff, maxsplit=1)
        message = message.strip()
        logger.debug("stripped message: %s",message)
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
            publish_mqtt(topic, payload)
        else:
            logger.debug("Message not type s: %s", message)


def publish_mqtt(key, payload):
    """Publish on MQTT."""
    logger.info("Outgoing on MQTT: %s %s", STATE_PREFIX + key, payload)
    client.publish(STATE_PREFIX + key, payload)


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


def on_disconnect(client, userdata, rc):
    """Try to recover MQTT"""
    logger.error("Disconnected with result code: %s", rc)
    reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
    while reconnect_count < MAX_RECONNECT_COUNT:
        logger.info("Reconnecting in %d seconds...", reconnect_delay)
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
    logger.info("Reconnect failed after %s attempts. Exiting...", reconnect_count)


def init_mqtt():
    """Initialize MQTT"""
    #TODO try kill on except
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    try:
        client.connect(BROKER_ADDRESS)
    except:
        logger.error("Could not connect to mqtt server.")
    client.loop_start()
    client.subscribe([("ard_state/#", 1), ("ard_command/#", 1)])


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

    
def main_loop():
    """Accept incomming connections. Start threads to handel them."""

    while not end_threads:
        try:
            client_socket, client_address = server_socket.accept()
            client_socket.settimeout(0.2)
        except socket.timeout:
            pass
        except:
            raise
        else:
            logger.info("Accepted connection from " + str(client_address)), 
            client_handler = threading.Thread(
                target=handle_client, args=(client_socket,))
            client_handler.start()
            client_socks.append(client_socket)
            client_threads.append(client_handler)


def main():
    """Main function"""

    init_socket(get_ip(), 8888)
    init_mqtt()
    signal.signal(signal.SIGINT, signal_handler)
    main_loop()
    shut_down()

    


if __name__ == "__main__":
    main()
