from pymodbus.client.sync import ModbusTcpClient
import time
import numpy as np

import serial_arduino


power_hist      = 20.0
weight_down     = 0.2
weight_up       = 0.02


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

    client = ModbusTcpClient('venus.fritz.box')
    setpoint_heat=0

    while 1:
        
        #get data from venus
        result =  client.read_input_registers(address=844, count=2, unit=0)
        print("state (0=idle;1=charging;2=discharging): ") 
        print(result.registers[0])
        ess_state =  result.registers[0]

        result =  client.read_input_registers(address=820, count=2, unit=0)
        print("Grid L1: ") 
        print(result.registers[0])
        grid_power = np.int16(result.registers[0])
        result =  client.read_input_registers(address=821, count=2, unit=0)
        print("Grid L2: ") 
        print(result.registers[0])
        grid_power += np.int16(result.registers[0])
        result =  client.read_input_registers(address=822, count=2, unit=0)
        print("Grid L3: ") 
        print(result.registers[0])
        grid_power += np.int16(result.registers[0])
        print("Grid power: ") 
        print(grid_power)
        
        #set target power depending on ess_state
        target_power=-10000   #like off
        if ess_state==0:
            target_power = -50    #battery is idle (close control)
        
        if ess_state==1:
            target_power = -100   #battery charging (carefull control)
            
        #control algorithm
        setpoint_heat = control_update(grid_power, setpoint_heat, target_power)
        print("setpoint: ")
        print(setpoint_heat)
        serial_arduino.pwm_setpoint(values["setpoint_heat"])
        time.sleep(1)
        
     
    
    client.close()