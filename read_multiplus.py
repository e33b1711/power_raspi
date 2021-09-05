from pymodbus.client.sync import ModbusTcpClient
import time

if __name__ == "__main__":

    client = ModbusTcpClient('venus.fritz.box')

    client

    while 1:
        result =  client.read_input_registers(address=842, count=2, unit=0)
        print("Bat Power: ") 
        print(result.registers[0])

        result =  client.read_input_registers(address=817, count=2, unit=0)
        print("Conszumption L1: ") 
        print(result.registers[0])
        result =  client.read_input_registers(address=818, count=2, unit=0)
        print("Conszumption L2: ") 
        print(result.registers[0])
        result =  client.read_input_registers(address=819, count=2, unit=0)
        print("Conszumption L3: ") 
        print(result.registers[0])
        
        result =  client.read_input_registers(address=844, count=2, unit=0)
        print("state (0=idle;1=charging;2=discharging): ") 
        print(result.registers[0])
        
        result =  client.read_input_registers(address=865, count=2, unit=0)
        print("charge current: ") 
        print(result.registers[0])
        
        
        result =  client.read_input_registers(address=307, count=2, unit=225)
        print("max charge  current: ") 
        print(result.registers[0])
        
        
        
        time.sleep(5)
    
    client.close()