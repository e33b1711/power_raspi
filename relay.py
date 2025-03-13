"""TCP relay ser"""
import socket
import threading
import argparse
import logging
import signal
import re
import time
from lib.get_ip import get_ip
from lib.git_revision import get_git_rev


# global stuff
end_threads = False
HEART_RATE = 60
last_haert_beat = 0
git_rev = get_git_rev()

# tcp stuff
clients: list = []
threads: list = []

PORT = 8888
VERBOSE_PORT = 8889


# logging stuff
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def filter_messages(messages):
    """Filter out state messages."""
    logger.debug("Filter messages...")
    messages_out = ""
    for message in messages:
        if message.startswith("!c!"):
            messages_out += message + "\n"
            logger.debug("Going through: %s", message)
        else:
            logger.debug("Filtered out: %s", message)

    return messages_out.encode()


def handle_client(client):
    """Client thread function"""

    while not end_threads:
        try:
            data = client.recv(1024)
        except socket.timeout:
            pass
        else:
            if not data:
                break
            message = data.decode('utf-8')
            logger.debug("Received message: %s", message)
            # relay to the others
            relay(filter_messages(get_message(message)), client, PORT)
            relay(data, client, VERBOSE_PORT)

    client.close()
    logger.info("Closing client thread.")


def relay(message, connection, port):
    """Relay message to all clients"""
    logger.debug("Relay on port %i", port)
    if message == "":
        return
    for client in clients:

        #TOD make me better
        if isinstance(client, socket.socket):
            client_port = client.getsockname()[1]
        else:
            client_port = 0

        if client != connection and client_port == port:
            logger.debug("Relay: %s", str(client))
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
    parts =  re.split(r'\$', mess_buff)
    return [part.strip() + "$" for part in parts if part.strip()]


def remove(client):
    """Remove client from list"""
    if client in clients:
        clients.remove(client)


def init(ip_address, port, verbose_port):
    """Open the socket"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.settimeout(0.2)
    server.bind((ip_address, port))
    server.listen(5)
    verbose_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    verbose_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    verbose_server.settimeout(0.2)
    verbose_server.bind((ip_address, verbose_port))
    verbose_server.listen(5)
    logger.info("Server listening on %s , %i and %i (verbose)", str(ip_address), port, verbose_port)
    return server, verbose_server


def signal_handler(sig, frame):
    """Clean up on exit"""
    logger.info('Closing down.')
    global end_threads
    end_threads = True


def shut_down(server, verbose_server):
    """End Threads. Close sockets."""

    logger.info('waiting for threads to close')
    for thread in threads:
        thread.join()
    logger.info('All threads closed. Good bye!')

    logger.info('Closing sockets...')
    server.close()
    verbose_server.close()
    logger.info('Closing sockets done.')


def beat_heart():
    """Send git rev message all n minutes."""
    global last_haert_beat
    if last_haert_beat + HEART_RATE < time.time():
        logger.info("Sending heart beat: %s", git_rev)
        message = "!s!relay_service!" + git_rev + "$"
        relay(message.encode(), None, VERBOSE_PORT)
        last_haert_beat = time.time()


def main_loop(server, verbose_server):
    """Accept incomming connections. Start threads to handel them."""

    while not end_threads:
        beat_heart()

        try:
            client_socket, client_address = server.accept()
            client_socket.settimeout(0.2)
        except socket.timeout:
            pass
        else:
            logger.info("Accepted connection from %s", str(client_address))
            client_handler = threading.Thread(
                target=handle_client, args=(client_socket,))
            client_handler.start()
            clients.append(client_socket)
            threads.append(client_handler)

        try:
            client_socket, client_address = verbose_server.accept()
            client_socket.settimeout(0.2)
        except socket.timeout:
            pass
        else:
            logger.info("Accepted connection from %s", str(client_address))
            client_handler = threading.Thread(
                target=handle_client, args=(client_socket,))
            client_handler.start()
            clients.append(client_socket)
            threads.append(client_handler)


def main():
    """Main function"""

    get_ip(exit_on_fail=True)
    server, verbose_server = init("0.0.0.0", 8888, 8889)
    signal.signal(signal.SIGINT, signal_handler)

    main_loop(server, verbose_server)
    shut_down(server, verbose_server)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-log',
                        '--loglevel',
                        default='info',
                        help='Provide logging level. Example --loglevel debug, default=info')
    args = parser.parse_args()
    logger.setLevel(level=args.loglevel.upper())
    main()
