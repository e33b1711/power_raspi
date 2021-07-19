#!/usr/bin/env python3

import serial_arduino
import mqtt_oh
import modbus_sdm630

import threading
import time
from datetime import datetime
now = datetime.now()



keys    = {"bal_power"}
values  = 

def update_values()
    #calculate auxilary values
    values[keys[1]] = modbus_sdm630.vales["p1_power"] + modbus_sdm630.vales["p2_power"] + modbus_sdm630.vales["p3_power"]
    
             
def print_values():
    print(values)
    
    
def info_loop()
    client = mqtt_oh.connect_mqtt()
    client.loop_start()
    while 1:
        time.sleep(5)
        for key in serial_arduino.keys:
            mqtt_oh.publish(client, "power_control/" + key, str(serial_arduino.arduino_values[key]))
        for key in modbus_sdm630.keys:
            mqtt_oh.publish(client, "power_control/" + key, str(modbus_sdm630.values[key]))  
        for key in keys:
            mqtt_oh.publish(client, "power_control/" + key, str(values[key])) 
        serial_arduino.print_values()
        modbus_sdm630.print_values()
        print_values()
    





if __name__ == "__main__":

    client = connect_mqtt()
    client.loop_start()
    
    serial_thread = threading.Thread(target=serial_arduino.read_loop)
    serial_thread.start()
    
    sdm_thread = threading.Thread(target=modbus_sdm630.sync_loop)
    sdm_thread.start()
    
    info_thread = threading.Thread(target=info_loop)
    info_thread.start()
    
    while 1:
        #control algorithm
        values["set_point"] = 100;
        serial_arduino.pwm_setpoint(values["set_point"])
        time.sleep(1)
        
        
        
        
