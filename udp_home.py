import socket
import time
from pymodbus.client.sync import ModbusTcpClient
import requests
from requests.exceptions import HTTPError
from requests.structures import CaseInsensitiveDict

#heating's stuff
HOST                    = "192.168.178.222"  # The server's hostname or IP address
PORT                    = 8888  # The port used by the server
heat_setpoint           = 0
heat_connection         = 0


#victron stuff
victron_host            = '192.168.178.144'
victron_connection      = 0
victron_pv_power        = 0
victron_heat_power      = 0
victron_soc             = 0
victron_state           = 0   #0=idle;1=charging;2=discharging


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
warp_connection         = 0

#set warp amps / get warp_power
def update_warp():
    global warp_setpoint          
    global warp_power            
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
    
    
#get the pv power / the power of the heating / the SOC form victron
def update_victron():
    global victron_host        
    global victron_connection  
    global victron_pv_power    
    global victron_heat_power  
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
        
        
        #0.1 scale factor, signed!!
        result =  client.read_input_registers(address=23, count=2, unit=228)
        #print("victron_heat_power: ") 
        #print(result.registers[0]*10)
        victron_heat_power= result.registers[0]*10
        
        client.close()
        victron_connection = 1
    except:
        victron_connection = 0
        print("Error: Could not connect to victron!")    

    
    


#TODO: force charging:  instant, power selecteable                      (infitly at f.e. 2500W)
#                       instant, with timeout and power selecteable     (f.e. for 6h at 2000W)
#                       ensure certain ammount of energy until          (f.e +30 kWh until tomorrow 0700)    



if __name__ == "__main__":
    
    while 1:
    
        #read infos
        update_victron()
        update_warp()
        
        #calc extra pv power, dependend on SOC and pv power
        extra_pv_power = victron_pv_power - 3000
        if victron_soc >= 95:
            extra_pv_power = victron_pv_power - 1000
        if victron_soc >= 99:
            extra_pv_power = victron_pv_power - 600
        if victron_soc == 100:
            extra_pv_power = victron_pv_power-400
        
        
        
       
        

        #wallbox has 6 amps min (1320W)
        #ev_extra_power < 13000 needs to be burned with elo heating
        #also some histeresis
        elo_only = 0
        if extra_pv_power < 1400:
            elo_only = 1
        if extra_pv_power > 2000:
            elo_only = 0
        
        delta_power = extra_pv_power - warp_power - victron_heat_power
        if elo_only==0:
            if delta_power > 200:
                if warp_setpoint < 16:
                    warp_setpoint +=1
                    if warp_setpoint<6:
                        warp_setpoint = 6
                else:
                    heat_setpoint +=5
                    
            if delta_power < -100:
                if heat_setpoint > 0:
                    heat_setpoint -=5
                else:
                    warp_setpoint -=1
                    if warp_setpoint<6:
                        warp_setpoint = 0
        else:
            if delta_power > 200:
                heat_setpoint +=5       
            if delta_power < -100:
                heat_setpoint -=5
                    
        #warp_setpoint = int(extra_pv_power / 220)
        #heat_setpoint = int(extra_pv_power / 3000 * 220)
        
        
        #if wallbox / victron / power is not avaible => bypass
        if victron_connection==0 or heat_connection==0 or warp_connection==0:
            heat_setpoint = 0
            warp_setpoint = 0

            
        #write to power sinks
        update_heat()
        update_warp()
        
        
        print("--------------------------------------------")
        print("warp_connection:    " + str(warp_connection))
        print("victron_connection: " + str(victron_connection))
        print("heat_connection:    " + str(heat_connection))
        print("----------------------")
        print("victron_soc:        " + str(victron_soc))
        print("victron_pv_power:   " + str(victron_pv_power))
        print("extra_pv_power:     " + str(extra_pv_power))
        print("victron_heat_power: " + str(victron_heat_power))
        print("warp_power:         " + str(warp_power))
        print("elo_only:           " + str(elo_only))
        print("delta_power:        " + str(delta_power))
        print("heat_setpoint:      " + str(heat_setpoint))
        print("warp_setpoint:      " + str(warp_setpoint))
        print("--------------------------------------------")
      
        
        time.sleep(10)
        
        
        
        
        