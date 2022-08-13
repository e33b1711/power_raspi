#!/usr/bin/env python3

import socket
import time
import paho.mqtt.client as mqtt
from pymodbus.client.sync import ModbusTcpClient
import requests
from requests.exceptions import HTTPError
from requests.structures import CaseInsensitiveDict
import signal
import sys

#victron stuff
victron_host            = '192.168.178.144'

#victron data
all_data = {
    'grid_power':               -1,           
    'solar_power':              -1,           
    'battery_power':            -1,         
    'loads_power':              -1,           
    'criticial_loads_power':    -1, 
    'victron_connected':        0,    
    'victron_status':           -1,        
    'state_of_charge':          -1,
    'charger_power':            -1,        
    'charger_setpoint':         -1,
    'charger_connected':        0,
    'charger_status':           -1
}    

victron_modbus = {
    'grid_power':               [820, 821, 822],           
    'solar_power':              [811, 812, 813],           
    'battery_power':            [842],         
    'loads_power':              [817, 818, 819],            
    'criticial_loads_power':    [23], 
    'victron_connected':        [],    
    'victron_status':           [844],        
    'state_of_charge':          [843]
}    

victron_unit = {
    'grid_power':               100,           
    'solar_power':              100,           
    'battery_power':            100,         
    'loads_power':              100,            
    'criticial_loads_power':    228, 
    'victron_connected':        100,    
    'victron_status':           100,        
    'state_of_charge':          100
} 

victron_scale = {
    'grid_power':               1,           
    'solar_power':              1,           
    'battery_power':            1,         
    'loads_power':              1,            
    'criticial_loads_power':    10, 
    'victron_connected':        1,    
    'victron_status':           1,        
    'state_of_charge':          1
}       


charger_addresses = {
    'charger_power':            0,        
    'charger_setpoint':         0,
    'charger_connected':        0,
    'charger_status':           0
   
}

#mqtt stuff
#state topics:  are just the dictonary names 
broker_address = "openhabianpi2.fritz.box"
mqtt_state_prefix = "power_state/"
client = mqtt.Client("P2")


def on_message(client, userdata, message):
    print("message received " ,str(message.payload.decode("utf-8")))
    print("message topic=",message.topic)
    print("message qos=",message.qos)
    print("message retain flag=",message.retain)
   

def to_signed(unsigned):
    if unsigned>2**15:
        return int(unsigned)-int(2**16)
    else:
        return int(unsigned)
        
    
#get the pv power / the power of the heating / the SOC form victron
def update_victron():
    global all_data
    global victron_modbus  

    #print("====update_victron===")    

    try:
        client = ModbusTcpClient(victron_host)
        
        for key in victron_modbus.keys():
            #print(key)
            all_data[key]=0
            for address in victron_modbus[key]:
                unit = victron_unit[key]
                scale = victron_scale[key]
                #print(str(address) + " / " + str(unit))
                result =  client.read_input_registers(address=address, count=2, unit=unit)
                #print(result)
                all_data[key] += to_signed(result.registers[0])*scale
        client.close()
        all_data['victron_connected'] = 1
    except Exception as e:
        print(e)
        all_data['victron_connected'] = 0
        print("Error: Could not connect to victron!")    
    
    #print("====update_victron===")
        
        
def print_alldata():
    print("====print_alldata===")
    for key in all_data.keys():
        print(key + ":" + str(all_data[key]))
    print("====print_alldata===")
        

def publish_mqtt():
    for key in all_data.keys():
        client.publish(mqtt_state_prefix + key, all_data[key])
    
       

    
    
if __name__ == "__main__":

    #mqtt
    client.on_message=on_message
    client.connect(broker_address)
    client.loop_start() 
    #client.subscribe(command_topic)

    while 1:
    
        #read infos
        update_victron()
        publish_mqtt()
        print_alldata();
        
        time.sleep(10)
        
        
        
        
        