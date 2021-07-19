#!/usr/bin/env python3

import serial_arduino
import mqtt_oh
import modbus_sdm630

import threading
import time
from datetime import datetime
now = datetime.now()



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
        #print("is: "+ str(values["setpoint_heat"]))
        update = values["setpoint_heat"] - 0.01*(values["power_bal"]+25.0)
        #print("update 0: " +str(update))
        if update >255:
            update = 255
        if update < 0:
            update = 0
        values["setpoint_heat"] = update
        #print("update:" + str(update))
        serial_arduino.pwm_setpoint(values["setpoint_heat"])
        
        
        
        
