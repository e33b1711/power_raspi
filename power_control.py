#!/usr/bin/env python3

import serial_arduino
import mqtt_oh

import threading

from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder



import logging
FORMAT = ('%(asctime)-15s %(threadName)-15s '
          '%(levelname)-8s %(module)-15s:%(lineno)-8s %(message)s')
logging.basicConfig(format=FORMAT)
log = logging.getLogger()
log.setLevel(logging.DEBUG)

UNIT = 0x1

import time


sdm630_info         = ["p1_power", "p2_power", "p3_power"]
sdm630_addresses    = [ 0x0C, 0x0E, 0x10]
sdm630_values       = [0, 0, 0]

             


def run_sync_client():

    client = ModbusClient(method='rtu', port='/dev/ttyUSB0', timeout=1, baudrate=9600)
    client.connect()

    
    for index in range(len(sdm630_info)):
        result =  client.read_input_registers(address=sdm630_addresses[index], count=2, unit=1)
    
        if result.isError():
            log.debug("Error reading " + sdm630_info[index])
        else:
            decoder = BinaryPayloadDecoder.fromRegisters(result.registers, wordorder=Endian.Big, byteorder=Endian.Big)
            sdm630_values[index] = decoder.decode_32bit_float()
            print(sdm630_info[index] + ": " + str(sdm630_values[index]))

    client.close()
    
    

    


if __name__ == "__main__":

    client = connect_mqtt()
    client.loop_start()
    
    thread = threading.Thread(target=serial_arduino.read_loop)
    thread.start()
    
    while 1:
        serial_arduino.print_values()
        run_sync_client()
        
        for key in serial_arduino.keys:
            publish(client, "power_control/" + key, str(serial_arduino.arduino_values[key]))
            
        publish(client, "power_control/balPower", str(sdm630_values[0] + sdm630_values[1] + sdm630_values[2]))   
        serial_arduino.pwm_setpoint(10)
        time.sleep(5)
        
        
        
        
