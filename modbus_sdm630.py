#!/usr/bin/env python3

from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder

import time


keys         = ["power_p1", "power_p2", "power_p3"]
addresses    = [ 0x0C, 0x0E, 0x10]
values       = {}

             
def print_values():
    print(values)

def sync_loop():
    print("Starting sync_loop")
    client = ModbusClient(method='rtu', port='/dev/ttyUSB0', timeout=1, baudrate=9600)
    client.connect()

    while 1:
        for index in range(len(addresses)):
            result =  client.read_input_registers(address=addresses[index], count=2, unit=1)
        
            if result.isError():
                print("sdm630 error")
            else:
                decoder = BinaryPayloadDecoder.fromRegisters(result.registers, wordorder=Endian.Big, byteorder=Endian.Big)
                values[keys[index]] = decoder.decode_32bit_float()
        time.sleep(0.2)
        
    client.close()
    
    

        
        
