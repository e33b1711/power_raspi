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
import array

#mqtt stuff
broker_address      = "openhabianpi2.fritz.box"
state_topic         = "power_state/heat_control"
command_topic       = "power_command/heat_control"
heat_power_topic    = "power_state/victron_heat_power"
soc_topic         = "power_state/soc"
client = mqtt.Client("P1")

#heating's stuff
HOST                    = "192.168.178.222"  # The server's hostname or IP address
PORT                    = 8888  # The port used by the server
heat_setpoint           = 0
heat_control_on         = 0
heat_connection         = 0

#heat power = (set_point-25)*2900/200
heat_constant = 15 #watts per pwm


def signal_handler(sig, frame):
    global heat_setpoint
    global heat_control_on
    heat_setpoint   = 0
    heat_control_on = 0
    update_heat()
    client.publish(state_topic,str(heat_control_on))
    client.loop_stop() 
    print('Exit...')
    sys.exit(0)


#victron stuff
victron_host            = '192.168.178.144'
victron_connection      = 0
#victron_pv_power        = 0
victron_heat_power      = 0
victron_mains_power     = 0
victron_battery_power   = 0
victron_soc             = 0
#victron_state           = 0     #0=idle;1=charging;2=discharging
victron_switch          = 0     #1 chrager / 2= inverter / 3=on / 4=off

def on_message(client, userdata, message):
    print("message received " ,str(message.payload.decode("utf-8")))
    print("message topic=",message.topic)
    print("message qos=",message.qos)
    print("message retain flag=",message.retain)
    
    payload = str(message.payload.decode("utf-8"))
    global heat_control_on
    
    if payload == "1":
        heat_control_on = 1
        #may not last long!
    if payload == "0":
        heat_control_on = 0



#set the pwm heating
def update_heat():
    global heat_connection

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            value = str(int(heat_setpoint))
            send_string = b'!w!P_EL!' + value.encode('ASCII') + b'$\n'
            #print(send_string)
            s.sendall(send_string)
            data = s.recv(1024)
            #print(f"Received {data!r}")
            heat_connection = 1
    except:
        heat_connection = 0
        print("Could not connect to echo server!")


def to_signed(unsigned):
    if unsigned>2**15:
        return int(unsigned)-int(2**16)
    else:
        return int(unsigned)
        
    
#get the pv power / the power of the heating / the SOC form victron
def update_victron():
    global victron_host        
    global victron_connection  
    #global victron_pv_power    
    global victron_heat_power  
    global victron_mains_power    
    global victron_battery_power 
    global victron_soc         
    #global victron_state 
    global victron_switch    

    try:
        client = ModbusTcpClient(victron_host)
        
        #result =  client.read_input_registers(address=844, count=2, unit=100)
        #print("state: ") 
        #print(result.registers[0])
        #victron_state = result.registers[0]
        
        result =  client.read_input_registers(address=33, count=2, unit=228)
        print("switch: ") 
        print(result.registers[0])
        victron_switch = result.registers[0]

        result =  client.read_input_registers(address=843, count=2, unit=100)
        #print("SOC: ") 
        #print(result.registers[0])
        victron_soc = result.registers[0]
        
        #result =  client.read_input_registers(address=812, count=2, unit=100)
        #print("PV power: ") 
        #print(result.registers[0])
        #victron_pv_power = result.registers[0]
        
        victron_mains_power = 0
        for add in [820, 821, 822]:
            result =  client.read_input_registers(address=add, count=2, unit=100)
            #print(to_signed(result.registers[0]))
            victron_mains_power += to_signed(result.registers[0])
        
        result =  client.read_input_registers(address=842, count=2, unit=100)
        #print("victron_battery_powerr: ") 
        #print(result.registers[0])
        victron_battery_power = to_signed(result.registers[0])
        
        
        #0.1 scale factor, signed!!
        result =  client.read_input_registers(address=23, count=2, unit=228)
        #print("victron_heat_power: ") 
        #print(result.registers[0]*10)
        victron_heat_power= to_signed(result.registers[0])*10
        
        client.close()
        victron_connection = 1
    except:
        victron_connection = 0
        print("Error: Could not connect to victron!")    

    
        



if __name__ == "__main__":

    signal.signal(signal.SIGINT, signal_handler)
    
    client.on_message=on_message
    client.connect(broker_address)
    client.loop_start() 
    client.subscribe(command_topic)

    heat_setpoint   = 0

    update_victron()
    update_heat()
    
  
    
    while 1:
    
        #read infos
        update_victron()
        
        
        #ess control goal
        victron_battery_power_goal = 0
        if victron_switch==3 or victron_switch==1:
            #charger on
            victron_battery_power_goal = 1800
            if victron_soc>95:
                victron_battery_power_goal = 500
            if victron_soc==100:
                victron_battery_power_goal = 0
        
        delta_power = -1* victron_mains_power -(victron_battery_power_goal-victron_battery_power)
        
        if delta_power > 50:
            heat_setpoint += (delta_power-50)/15
            
        if delta_power < 0:
            heat_setpoint += (delta_power-50)/10
        
        if heat_setpoint<0:
            heat_setpoint = 0
        
        if heat_setpoint>220:
            heat_setpoint = 220
             

        #if wallbox / victron / power is not avaible => bypass
        if victron_connection==0 or heat_connection==0:   
            heat_control_on = 0    
        
        if heat_control_on==0:
            heat_setpoint   = 0  
            heat_control_on     = 0            
            
        #write to power sinks
        update_heat()
        
        #publish state
        client.publish(state_topic,str(heat_control_on))
        client.publish(heat_power_topic,victron_heat_power/1000)
        client.publish(soc_topic,victron_soc)
        
        
        print("--------------------------------------------")
        print("victron_connection:    " + str(victron_connection))
        print("heat_connection:       " + str(victron_heat_power))
        print("--------------------------------")
        print("victron_soc:           " + str(victron_soc))
        #print("victron_state:         " + str(victron_state))
        print("victron_switch:        " + str(victron_switch))
        #print("victron_pv_power:      " + str(victron_pv_power))
        print("victron_mains_power:   " + str(victron_mains_power))
        print("victron_battery_power: " + str(victron_battery_power))
        print("victron_heat_power:    " + str(victron_heat_power))
        print("--------------------------------")
        print("victron_battery_power_goal: " + str(victron_battery_power_goal))
        print("delta_power:                " + str(delta_power))
        print("heat_setpoint:              " + str(heat_setpoint))
        print("heat_control_on:            " + str(heat_control_on))
        print("--------------------------------------------")

 
        time.sleep(5)
    
        
        
        
        