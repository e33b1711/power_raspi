"""Set PWM """
import socket
import logging
import time

MAX_SETPOINT = 220
MIN_SETPOINT = 10
POWER2SP = 220 / 3000
HOST = "192.168.178.23"
PORT = 8888

def set_heat(power):
    """Set pwm heat over echo server"""
    setpoint = min(power * POWER2SP, MAX_SETPOINT)
    if setpoint < MIN_SETPOINT:
        setpoint = 0
    logging.info("Setting pwm, setpoint %i, power %i", setpoint, power)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            value = str(int(setpoint))
            send_string = b'!c!U_EL!' + value.encode('ASCII') + b'$\n'
            s.sendall(send_string)
            s.close()
            return True
    except Exception as e:
        logging.error(e)
        return False


if __name__ == "__main__":
    logging.basicConfig(level=0)
    for set_power in range(-100, 4000, 100):
        set_heat(set_power)
        time.sleep(2)
