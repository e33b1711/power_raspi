#!/usr/bin/env python3

#TODO
#wallbox get infos      (x)
#wallbox set            (x)
#heat set               (x)
#mqtt receive           (x)
#algo                   ()


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

all_data = {
    #collected data
    'grid_power':               -1,           
    'solar_power':              -1,           
    'battery_power':            -1,         
    'loads_power':              -1,           
    'criticial_loads_power':    -1,
    'ess_setpoint':             0,
    'victron_connected':        0,    
    'victron_status':           -1,        
    'state_of_charge':          -1,
    'charger_power':            -1,        
    'charger_setpoint':         -1,
    'charger_connected':        0,
    'charger_status':           -1,
    'heat_connected':           -1,
    
    #own data
    'solar2heat':               "OFF",
    'solar2car':                "OFF",
    'car_connected':            "OFF",
    'charging':                 "OFF"
}    

victron_modbus = {
    'grid_power':               [820, 821, 822],           
    'solar_power':              [811, 812, 813],           
    'battery_power':            [842],         
    'loads_power':              [817, 818, 819],            
    'criticial_loads_power':    [23], 
    'ess_setpoint':             [2700],
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
    'ess_setpoint':             100,    
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
    'ess_setpoint':             1,     
    'victron_connected':        1,    
    'victron_status':           1,        
    'state_of_charge':          1
}       

#charger stuff
charger_keys = {
    'power':                        'charger_power',        
    'allowed_charging_current':     'charger_setpoint',        
    'vehicle_state':                'charger_status'        
}

charger_scale = {
    'charger_power':        1,        
    'charger_setpoint':     0.001,        
    'charger_status':       1        
}

url_meter       = 'http://192.168.178.43/meter/state'
url_controller  = 'http://192.168.178.43/evse/state'




url_limit = 'http://192.168.178.43/evse/current_limit'
url_stop = 'http://192.168.178.43/evse/stop_charging'
url_start = 'http://192.168.178.43/evse/start_charging'
headers = CaseInsensitiveDict()
headers["Content-Type"] = "application/json"
data_null = 'null'

def signal_handler(sig, frame):
    all_data['solar2heat']  = 0
    all_data['solar2car']   = 0

    #set ess setpoint to 0
    victron_setpoint(0)
    
    #turn off charger set to 10A
    charger_off()
    set_charger(10)
    
    #publish mqtt control states
    read_victron()
    read_charger()
    all_data['charger_connected']  = 0
    all_data['victron_connected']  = 0
    all_data['heat_connected']  = 0
    publish_mqtt()
    
    print('Exit...')
    sys.exit(0)
    
    

def read_charger():
    try:
        
        response = requests.get(url_meter)
        response.raise_for_status()
        jsonResponse = response.json()
        for key, value in jsonResponse.items():
            #print(key, ":", value)
            for rev_key in charger_keys:
                if key == rev_key:
                    all_data[charger_keys[rev_key]] = value*charger_scale[charger_keys[rev_key]]

        response = requests.get(url_controller)
        response.raise_for_status()
        jsonResponse = response.json()
        for key, value in jsonResponse.items():
            #print(key, ":", value)
            for rev_key in charger_keys:
                if key == rev_key:
                    all_data[charger_keys[rev_key]] = value*charger_scale[charger_keys[rev_key]]
      
        all_data['charger_connected']  = 1
        
    except HTTPError as http_err:
        all_data['charger_connected']  = 0
        print(f'HTTP error occurred: {http_err}')
    except Exception as err:
        all_data['charger_connected']  = 0
        print(f'Other error occurred: {err}')

    
def set_charger(setpoint):
    print("================set_charger=========================") 
    try:
        #set amps
        data = '{"current":' + str(int(setpoint)) + '000}'
        response = requests.put(url_limit, headers=headers, data=data)
        response.raise_for_status()
        all_data['charger_connected']  = 1
    except HTTPError as http_err:
        all_data['charger_connected']  = 0
        print(f'HTTP error occurred: {http_err}')
    except Exception as err:
        all_data['charger_connected']  = 0
        print(f'Other error occurred: {err}')
        
def charger_on():
    print("================charger_on=========================") 
    try:
        response = requests.put(url_start, headers=headers, data=data_null)
        response.raise_for_status()      
        all_data['charger_connected']  = 1
    except HTTPError as http_err:
        all_data['charger_connected']  = 0
        print(f'HTTP error occurred: {http_err}')
    except Exception as err:
        all_data['charger_connected']  = 0
        print(f'Other error occurred: {err}')
        
def charger_off():
    print("================charger_off=========================") 
    try:
        response = requests.put(url_stop, headers=headers, data=data_null)
        response.raise_for_status()      
        all_data['charger_connected']  = 1
    except HTTPError as http_err:
        all_data['charger_connected']  = 0
        print(f'HTTP error occurred: {http_err}')
    except Exception as err:
        all_data['charger_connected']  = 0
        print(f'Other error occurred: {err}')


def to_signed(unsigned):
    if unsigned>2**15:
        return int(unsigned)-int(2**16)
    else:
        return int(unsigned)




#mqtt stuff
#state topics:  are just the dictonary names 
broker_address = "localhost"
mqtt_state_prefix = "power_state/"
client = mqtt.Client("power_control")
command_topics = ["power_command/solar2heat", "power_command/solar2car", "power_command/charger_setpoint", "power_command/charging"];


def on_message(client, userdata, message):
    print("message received " ,str(message.payload.decode("utf-8")))
    print("message topic=",message.topic)
    print("message qos=",message.qos)
    print("message retain flag=",message.retain)
    payload = str(message.payload.decode("utf-8"))
    
    if message.topic==command_topics[0]:
        key = 'solar2heat'
        all_data[key] = message.payload.decode("utf-8")
        client.publish(mqtt_state_prefix + key, all_data[key])
    if message.topic==command_topics[1]:
        key = 'solar2car'
        all_data[key] = message.payload.decode("utf-8")
        client.publish(mqtt_state_prefix + key, all_data[key])
    if message.topic==command_topics[2]:
        if not(all_data['solar2car']=="ON" or all_data['solar2car']=="1"):
            key='charger_setpoint'
            payload_val = int(message.payload.decode("utf-8"))
            print(payload_val)
            set_charger(round(payload_val)) 
            read_charger()
            client.publish(mqtt_state_prefix + key, all_data[key])
    if message.topic==command_topics[3]:
        if not(all_data['solar2car']=="ON" or all_data['solar2car']=="1"):
            key='charging'
            payload_val = message.payload.decode("utf-8")
            print(payload_val)
            if payload_val=="ON" or payload_val=='1': 
                charger_on()
            if payload_val=="OFF" or payload_val=='0': 
                charger_off()    
            read_charger()
            client.publish(mqtt_state_prefix + key, all_data[key])
        
   

def to_signed(unsigned):
    if unsigned>2**15:
        return int(unsigned)-int(2**16)
    else:
        return int(unsigned)
        
    
#get the pv power / the power of the heating / the SOC form victron
def victron_setpoint(setpoint):
    try:
        client = ModbusTcpClient(victron_host)
        key         = "ess_setpoint"
        address     = victron_modbus[key]
        unit = victron_unit[key]
        client.write_register(address=address[0], unit=unit, value=setpoint)
        client.close()
        all_data['victron_connected'] = 1
        
    except Exception as e:
        print(e)
        all_data['victron_connected'] = 0
        print("Error: Could not connect to victron!")    
    
    #print("====update_victron===")

def read_victron():
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
        
        
#set the pwm heating
HOST                    = "192.168.178.23"  # The server's hostname or IP address
PORT                    = 8888  # The port used by the server   
heat_setpoint_local     = 0
last_sp_local 			= 0
def update_heat(delta_power):
    global heat_setpoint_local
    global last_sp_local
    heat_setpoint_local += round(delta_power *(220/3000)*0.5);
    if heat_setpoint_local > 220:
        heat_setpoint_local = 220
    if heat_setpoint_local < 10:
        heat_setpoint_local = 0
        
    print("========================================")
    print("delta_power:          " + str(delta_power))
    print("increment:            " +  str(round(delta_power *(220/3000)*0.2)))
    print("heat_setpoint_local:  " + str(heat_setpoint_local))
    print("=========================================")      
   
    if not(heat_setpoint_local == 0 and last_sp_local==0):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((HOST, PORT))
                value = str(int(heat_setpoint_local))
                send_string = b'!c!U_EL!' + value.encode('ASCII') + b'$\n'
                #print(send_string)
                s.sendall(send_string)
                data = s.recv(1024)
                #print(f"Received {data!r}")
        except Exception as e:
            print(e)
            print("Could not connect to echo server!")
		
    last_sp_local = heat_setpoint_local


def update_charger(power):
    
    setpoint =  round(power / 240)
    if setpoint>20:
        setpoint = 20
    if setpoint<0:
        setpoint = 0
      
    if round(setpoint)!=round(all_data['charger_setpoint']) and round(setpoint)>=6:
        set_charger(setpoint)
    
    if setpoint>=6 and all_data['charger_status']==1:
        charger_on()
    if setpoint<4 and all_data['charger_status']==2:
        charger_off()
        
    print("==================update_charger======================")
    print("setpoint:               " + str(setpoint))
    print("=========================================")      
    

    
    
if __name__ == "__main__":

    #gracefull strg+c
    signal.signal(signal.SIGINT, signal_handler)
       

    #mqtt
    client.on_message=on_message
    client.connect(broker_address)
    client.loop_start() 
    for topic in command_topics:
        client.subscribe(topic)
    
    #local variable not visible over mqtt
    first               = 1
    solar_power_mean    = 0

    while 1:
    
        #read infos
        read_victron()
        read_charger()
        
        if all_data['charger_status']==0:
            all_data['car_connected']=0
            all_data['charging']="OFF"
            all_data['solar2car']=="ON"
        if all_data['charger_status']==1:
            all_data['car_connected']=1
            all_data['charging']="OFF"
        if all_data['charger_status']==2:
            all_data['car_connected']=1
            all_data['charging']="ON"
        
        
        publish_mqtt()
        print_alldata()
        read_charger()
        
        #calculate delta power
        delta_power = 0;
        if all_data['state_of_charge']>90:
            delta_power = -1*all_data['grid_power'] - 1650/10*(100-int(all_data['state_of_charge'])) + all_data['battery_power']
        else:
            delta_power = -1*all_data['grid_power'] - 1650 + all_data['battery_power']
            
        #calculate mean solar power        
        if first:
            first=0
            solar_power_mean = all_data['solar_power']
        else:
            solar_power_mean += 0.01*(all_data['solar_power']-solar_power_mean)        
     
        print("========================================");
        print("delta_power:      " + str(delta_power));
        print("solar_power_mean: " + str(solar_power_mean))
        print("=========================================");      
            
            
        
        
        if all_data['solar2heat']=="ON" or all_data['solar2heat']=="1":
            update_heat(delta_power);

        
        
        
        
        if all_data['solar2car']=="ON" or all_data['solar2car']=="1":
            update_charger(solar_power_mean-500)   #debug
            if all_data['ess_setpoint'] !=0:
                    victron_setpoint(0)
        else:
            #charge from the grid / dont drain the battery
            if abs(all_data['charger_power'] - all_data['ess_setpoint'])>200:
                victron_setpoint(int(all_data['charger_power']))

        
        time.sleep(5)
        
        
        
        
        
