import socket
import time
from pymodbus.client.sync import ModbusTcpClient

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




#set the pwm heating
def update_heat():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            value = str(int(setpoint_heat))
            send_string = b'!w!P_EL!' + value.encode('ASCII') + b'$\n'
            print(send_string)
            s.sendall(send_string)
            data = s.recv(1024)
            print(f"Received {data!r}")
            heat_connection = 1
    except:
        heat_connection = 0
        print("Could not connect to echo server!")
    
    
#get the pv power / the power of the heating / the SOC form victron
def update_victron():
    try:
        client = ModbusTcpClient(victron_host)
        
        result =  client.read_input_registers(address=844, count=2, unit=100)
        print("state: ") 
        print(result.registers[0])
        victron_state = result.registers[0]

        result =  client.read_input_registers(address=843, count=2, unit=100)
        print("SOC: ") 
        print(result.registers[0])
        victron_soc = result.registers[0]
        
        result =  client.read_input_registers(address=812, count=2, unit=100)
        print("PV power: ") 
        print(result.registers[0])
        victron_pv_power = result.registers[0]
        
        
        #0.1 scale factor, signed!!
        result =  client.read_input_registers(address=23, count=2, unit=228)
        print("victron_heat_power: ") 
        print(result.registers[0]*10)
        victron_heat_power= result.registers[0]*10
        
        client.close()
        victron_connection = 1
    except:
        victron_connection = 0
        print("Could not connect to victron!")    

    
    


#set the amps of the wallbox


#get the power and the status of connection from the wallbox



if __name__ == "__main__":

    setpoint_heat = 80
    
    while 1:
        update_heat()
        update_victron()
        #setpoint_heat += 10
        time.sleep(10)
        
    #calc extra pv power, dependend on SOC and pv power

    #try to blow this power with the wallbox (first, is pv controled charging is avaible) / the elo heating (second)
    
    #if wallbox / victron / power is not avaible => bypass
        
        
        
        
        