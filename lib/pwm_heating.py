"""Set PWM """
import socket
import logging
import time

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

MAX_SETPOINT = 220
MIN_SETPOINT = 10
POWER_2_PWM = 220/3000
HOST = "192.168.178.23"
PORT = 8888

def set_heat(setpoint):
    """Set pwm heat over echo server"""
    if setpoint < MIN_SETPOINT:
        setpoint = 0
    logger.info("Setting pwm, setpoint %i", setpoint)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            value = str(int(setpoint))
            send_string = b'!c!U_EL!' + value.encode('ASCII') + b'$\n'
            s.sendall(send_string)
            s.close()
            return True
    except Exception as e:
        logger.error(e)
        return False


if __name__ == "__main__":
    logger.basicConfig(level=0)
    for set_power in range(0, 250, 10):
        set_heat(set_power)
        time.sleep(2)
