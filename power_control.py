#!/usr/bin/env python3

import serial_arduino
import mqtt_oh
import modbus_sdm630

import threading
import time
from datetime import datetime
now = datetime.now()

power_target    = 25.0
power_hist      = 10.0
weight_down     = 0.1
weight_up       = 0.01



keys    = {"power_bal", "setpoint_heat"}
values  = {}

def update_values():
    #calculate auxilary values
    values["power_bal"] = modbus_sdm630.values["power_p1"] + modbus_sdm630.values["power_p2"] + modbus_sdm630.values["power_p3"]
    
             
def print_values():
    print(values)
    
    
def info_loop():
    client = mqtt_oh.connect_mqtt()
    client.loop_start()
    while 1:
        time.sleep(5)
        serial_arduino.print_values()
        modbus_sdm630.print_values()
        print_values()
        for key in serial_arduino.keys:
            mqtt_oh.publish(client, "power_control/" + key, str(serial_arduino.values[key]))
        for key in modbus_sdm630.keys:
            mqtt_oh.publish(client, "power_control/" + key, str(modbus_sdm630.values[key]))  
        for key in keys:
            mqtt_oh.publish(client, "power_control/" + key, str(values[key])) 
    

def control_update(power_bal, setpoint_heat):
    power_diff = power_bal + power_target;
    print("power_diff: " + str(power_diff))
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
    print("setpoint_update: " + str(setpoint_update))
    return setpoint_update
            




if __name__ == "__main__":
    
    serial_thread = threading.Thread(target=serial_arduino.read_loop)
    serial_thread.start()
    
    sdm_thread = threading.Thread(target=modbus_sdm630.sync_loop)
    sdm_thread.start()
    
    info_thread = threading.Thread(target=info_loop)
    info_thread.start()
    
    values["setpoint_heat"] = 0.0

    time.sleep(2)

    while 1:
        #control algorithm
        update_values()
        time.sleep(1)
        values["setpoint_heat"] = control_update(values["power_bal"], values["setpoint_heat"])
        serial_arduino.pwm_setpoint(values["setpoint_heat"])
        
        
        
        
