"""Find primary IP"""
import socket
import sys
import logging

# logging stuff
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def get_ip(exit_on_fail=True):
    """Get primary IP adddress of this host"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(('10.254.254.254', 1))
        ip = s.getsockname()[0]
    except Exception as e:
        logger.error(e)
        ip = '127.0.0.1'
    finally:
        s.close()
    if exit_on_fail and ip == '127.0.0.1':
        sys.exit(-1)
    return ip
