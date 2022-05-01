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
victron_connection      = 0
victron_pv_power        = 0
victron_heat_power      = 0
victron_mains_power     = 0
victron_battery_power   = 0
victron_soc             = 0
victron_state           = 0   #0=idle;1=charging;2=discharging

#mqtt stuff
broker_address      = "openhabianpi2.fritz.box"
state_topic         = "power_state/pv_charge_bypass"
command_topic       = "power_command/pv_charge_bypass"
power_topic         = "power_state/wallbox_power"
solar_power_topic   = "power_state/solar_power"
client = mqtt.Client("P2")


#wallbox stuff
url_meter       = 'http://192.168.178.43/meter/state'
url_controller  = 'http://192.168.178.43/evse/state'
#payload = open("request.json")
#headers = {'content-type': 'application/json', 'Accept-Charset': 'UTF-8'}
#r = requests.post(url, data=payload, headers=headers)
url_limit = 'http://192.168.178.43/evse/current_limit'
url_stop = 'http://192.168.178.43/evse/stop_charging'
url_start = 'http://192.168.178.43/evse/start_charging'
headers = CaseInsensitiveDict()
headers["Content-Type"] = "application/json"
#data = '{"current":14000}'
data_null = 'null'

warp_setpoint           = 0
warp_power              = 0
warp_energy_counter     = 0
warp_connection         = 0
bypass                  = 0         #load without pv control

def signal_handler(sig, frame):
    global warp_setpoint
    global bypass
    bypass = 1
    heat_control_on = 0
    warp_setpoint = 20
    try:
        response = requests.put(url_stop, headers=headers, data=data_null)
        response.raise_for_status()
        data = '{"current":' + str(warp_setpoint) + '000}'
        response = requests.put(url_limit, headers=headers, data=data)
        response.raise_for_status()
    except HTTPError as http_err:
        warp_connection=0
        print(f'HTTP error occurred: {http_err}')
    except Exception as err:
        warp_connection=0
        print(f'Other error occurred: {err}')
    client.publish(state_topic,str(bypass))
    print('Exit...')
    sys.exit(0)
    
def on_message(client, userdata, message):
    print("message received " ,str(message.payload.decode("utf-8")))
    print("message topic=",message.topic)
    print("message qos=",message.qos)
    print("message retain flag=",message.retain)
    
    payload = str(message.payload.decode("utf-8"))
    global bypass
    
    if payload == "1":
        bypass = 1
        #may not last long!
    if payload == "0":
        bypass = 0

#set warp amps / get warp_power
def update_warp():
    global warp_setpoint          
    global warp_power  
    global warp_energy_counter      
    global warp_connection  
    
    #print("------------------------")

    try:
        
        #read meter
        response = requests.get(url_meter)
        response.raise_for_status()
        # access JSOn content
        jsonResponse = response.json()
        #print("Entire JSON response")
        #print(jsonResponse)
        #print("Print each key-value pair from JSON response")
        for key, value in jsonResponse.items():
            #print(key, ":", value)
            if key=='power':
                warp_power = value
            if key=='energy_rel':
                warp_energy_counter = value
            if key=='state':
                if value!=2:
                    warp_connection=0
                    print('warp meter offline')
                    raise
        #set amps
        if warp_setpoint<6:
            response = requests.put(url_stop, headers=headers, data=data_null)
            response.raise_for_status()
        else:
            response = requests.put(url_start, headers=headers, data=data_null)
            response.raise_for_status()
            data = '{"current":' + str(warp_setpoint) + '000}'
            response = requests.put(url_limit, headers=headers, data=data)
            response.raise_for_status()
      
        warp_connection         = 1  
        
    except HTTPError as http_err:
        warp_connection=0
        print(f'HTTP error occurred: {http_err}')
    except Exception as err:
        warp_connection=0
        print(f'Other error occurred: {err}')
    #print("------------------------")
   

def to_signed(unsigned):
    if unsigned>2**15:
        return int(unsigned)-int(2**16)
    else:
        return int(unsigned)
        
    
#get the pv power / the power of the heating / the SOC form victron
def update_victron():
    global victron_host        
    global victron_connection  
    global victron_pv_power    
    global victron_heat_power  
    global victron_mains_power    
    global victron_battery_power 
    global victron_soc         
    global victron_state       

    try:
        client = ModbusTcpClient(victron_host)
        
        result =  client.read_input_registers(address=844, count=2, unit=100)
        #print("state: ") 
        #print(result.registers[0])
        victron_state = result.registers[0]

        result =  client.read_input_registers(address=843, count=2, unit=100)
        #print("SOC: ") 
        #print(result.registers[0])
        victron_soc = result.registers[0]
        
        result =  client.read_input_registers(address=812, count=2, unit=100)
        #print("PV power: ") 
        #print(result.registers[0])
        victron_pv_power = result.registers[0]
        
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

    
    


#TODO: force charging:  instant, power selecteable                      (infitly at f.e. 2500W)
#                       instant, with timeout and power selecteable     (f.e. for 6h at 2000W)
#                       ensure certain ammount of energy until          (f.e +30 kWh until tomorrow 0700)    



if __name__ == "__main__":

    signal.signal(signal.SIGINT, signal_handler)
    
    #mqtt
    client.on_message=on_message
    client.connect(broker_address)
    client.loop_start() 
    client.subscribe(command_topic)

    
    #this will be paramters
    bypass_setpoint     = 20        #setpoint during bypass
    bypass_energy       = 6         #amount of energy to laod in bypass
    
    warp_setpoint       = 0
    warp_energy         = 0         #loaded til start 
    
    update_victron()
    update_warp()
    
    warp_energy_zero = warp_energy_counter
    
    victron_pv_power_smooth = victron_pv_power
    
    
    while 1:
    
        #read infos
        update_victron()
        update_warp()
        
        warp_energy = warp_energy_counter - warp_energy_zero
        
        #smooth pv power
        victron_pv_power_smooth = 0.95*victron_pv_power_smooth + 0.05*victron_pv_power
        
        #calc extra pv power, dependend on SOC and pv power
        extra_pv_power = round(victron_pv_power_smooth) - 2400
        if victron_soc >= 95:
            extra_pv_power = round(victron_pv_power_smooth) - 1000
        if victron_soc >= 99:
            extra_pv_power = round(victron_pv_power_smooth) - 400
        delta_power = extra_pv_power - warp_power
       
       
        #TODO: some hysteresis / delay between charge / no charge
       
        if bypass==0:
            if extra_pv_power > 1400:
                if delta_power > 200:
                    if warp_setpoint < 20:
                        warp_setpoint +=1
                    if warp_setpoint<6:
                        warp_setpoint = 6
                            
                if delta_power < -100:
                    warp_setpoint -=1
                    if warp_setpoint<6:
                        warp_setpoint = 0
            else:
                warp_setpoint = 0
        else:
            warp_setpoint = bypass_setpoint
            if warp_energy > bypass_energy:
                bypass = 0
            
        
        #if wallbox / victron / power is not avaible => bypass
        if victron_connection==0 or warp_connection==0:
            warp_setpoint = 0

            
        #write to power sinks
        update_warp()
        
        #mqtt
        client.publish(state_topic,str(bypass))
        client.publish(power_topic,warp_power/1000)
        client.publish(solar_power_topic,victron_pv_power/1000)
        
        
        print("--------------------------------------------")
        print("warp_connection:         " + str(warp_connection))
        print("victron_connection:      " + str(victron_connection))
        print("--------------------------------")
        print("victron_soc:             " + str(victron_soc))
        print("victron_state:           " + str(victron_state))
        print("victron_pv_power:        " + str(victron_pv_power))
        print("victron_mains_power:     " + str(victron_mains_power))
        print("victron_battery_power:   " + str(victron_battery_power))
        print("victron_heat_power:      " + str(victron_heat_power))
        print("warp_power:              " + str(warp_power))
        print("warp_energy_counter:     " + str(warp_energy_counter)) 
        print("--------------------------------")
        print("warp_energy:             " + str(warp_energy))
        print("victron_pv_power_smooth: " + str(victron_pv_power_smooth))
        print("extra_pv_power:          " + str(extra_pv_power))
        print("bypass:                  " + str(bypass))
        print("delta_power:             " + str(delta_power))
        print("warp_setpoint:           " + str(warp_setpoint))
        print("--------------------------------------------")
      
        
        time.sleep(10)
        
        
        
        
        