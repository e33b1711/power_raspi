#!/usr/bin/env python3

from pymodbus.client.sync import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
import time
import numpy as np
import signal
import sys

import serial_arduino

#TODO: handle modbus errors
#TODO: tighter control loop if battery is full (BUT: how to not prevent absorbtion)
#TODO: read back values form arduino (temp high / low)


power_hist      = 20.0
weight_down     = 0.2
weight_up       = 0.02
power_on        = -200   #grid power value to turn on heat control
count_on        = 10     #how often we need to see control on condition
count_off       = 3      #how often we need to see control off condition
target_power    = -100   #battery charging (carefull control)


venus_client    = ModbusTcpClient('venus.fritz.box')
sdm_client      = ModbusTcpClient('127.0.0.1')


def signal_handler(sig, frame):
    print('Closing modbus clients...')
    venus_client.close()
    sdm_client.close()
    sys.exit(0)
    

def control_update(grid_power, setpoint_heat, target_power):
    power_diff = grid_power - target_power
    #print("power_bal: " + str(power_bal))
    #print("power_diff: " + str(power_diff))
    #histeresys
    if abs(power_diff) < power_hist:
        setpoint_update = setpoint_heat
    else:
        if power_diff > 0:
            setpoint_update = setpoint_heat - weight_down * power_diff
        else:
            setpoint_update = setpoint_heat - weight_up * power_diff
            
    #saturate
    if setpoint_update > 255:
        setpoint_update = 255
    
    if setpoint_update<0:
        setpoint_update = 0
    #print("setpoint_update: " + str(setpoint_update))
    return setpoint_update





if __name__ == "__main__":
    
    signal.signal(signal.SIGINT, signal_handler)

    setpoint_heat   = 0     #pwm heat setpoint
    control_state   = 0     #0=heat control off (ESS on) / 1=heat control on (ESS charge only)
    trans_count     = 0
    last_time       = time.time()
    this_time       = time.time()
    
    #set ESS to charge / invert
    result = venus_client.write_register(address=33, value=3, unit=228) 

    while 1:
        #ensure 1 second cycle time
        this_time = time.time()
        if last_time + 1 > this_time:
            time.sleep(0.05)
        else:
            last_time = this_time
        
            #get data from venus
            result =  venus_client.read_input_registers(address=844, count=2, unit=0)
            print("state (0=idle;1=charging;2=discharging): " + str(result.registers[0])) 
            #print(result.registers[0])
            ess_state =  result.registers[0]
        
            #grid power is read directly from meter
            result =  sdm_client.read_input_registers(address=0x0C, count=2, unit=1)
            print(result.isError())
            decoder = BinaryPayloadDecoder.fromRegisters(result.registers, wordorder=Endian.Big, byteorder=Endian.Big)
            l1_power = decoder.decode_32bit_float()
            #print("Grid L1: ") 
            #print(l1_power)
            grid_power = l1_power
            
            result =  sdm_client.read_input_registers(address=0x0E, count=2, unit=1)
            print(result.isError())
            decoder = BinaryPayloadDecoder.fromRegisters(result.registers, wordorder=Endian.Big, byteorder=Endian.Big)
            l2_power = decoder.decode_32bit_float()
            #print("Grid L2: ")
            #print(l2_power)
            grid_power += l2_power

            result =  sdm_client.read_input_registers(address=0x10, count=2, unit=1)
            print(result.isError())
            decoder = BinaryPayloadDecoder.fromRegisters(result.registers, wordorder=Endian.Big, byteorder=Endian.Big)
            l3_power = decoder.decode_32bit_float()
            #print("Grid L3: ")
            #print(l3_power)
            grid_power += l3_power

            print("Grid power: " + str(grid_power)) 
        
        
            if control_state==0:
                print("heat control is off.")
                #heat is off
                setpoint_heat=0
                #we want to see negative grid power several times
                if grid_power < power_on:
                    trans_count +=1
                else:
                    trans_count = 0

                if trans_count > count_on:
                    #turn control on
                    control_state  = 1
                    trans_count    = 0
                    venus_client.write_register(address=33, value=1, unit=228) #set to charger only to prevent feed in during heat control
                    print("turning heat control on")

            if control_state==1:
                print("heat control is on.")
                #control algorithm
                setpoint_heat = control_update(grid_power, setpoint_heat, target_power)
                #grid feed in and heating completly off
                if grid_power>0 and setpoint_heat==0:
                    trans_count +=1
                else:
                    trans_count = 0
                if trans_count > count_off:
                    #turn control on
                    control_state  = 0
                    trans_count    = 0
                    setpoint_heat  = 0
                    venus_client.write_register(address=33, value=3, unit=228) #set back to on (charger & inverter)
                    print("turning heat control off")
                    #TODO: turn ESS to charge / discharge
                    
            #write pwm 
            print("setpoint: " + str(setpoint_heat))
            serial_arduino.pwm_setpoint(setpoint_heat)

     
    
    
