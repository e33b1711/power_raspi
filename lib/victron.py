"""Interface to Victron Multiplus 2"""
import logging
from pymodbus.constants import Endian
from pymodbus.client import ModbusTcpClient
from pymodbus.payload import BinaryPayloadDecoder

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

MAX_BATT_IN_POWER = 1650
HOST = '192.168.178.144'
PORT = 502

addresses = {
    'grid_power':               [820, 821, 822],           
    'solar_power':              [811, 812, 813],           
    'battery_power':            [842],         
    'loads_power':              [817, 818, 819],            
    'criticial_loads_power':    [23], 
    'ess_setpoint':             [2700],  
    'victron_status':           [844],        
    'state_of_charge':          [843]
}

register_type = {
    'grid_power':               'int16',           
    'solar_power':              'uint16',           
    'battery_power':            'int16',         
    'loads_power':              'uint16',            
    'criticial_loads_power':    'int16', 
    'ess_setpoint':             'int16',  
    'victron_status':           'uint16',        
    'state_of_charge':          'uint16'
}

units = {
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

scales = {
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


def read_victron():
    "Read some values form the MP2"
    try:
        client = ModbusTcpClient(HOST, port=PORT)
        client.connect()
        return_value = {}
        for key, address in addresses.items():
            return_value[key]=0
            for address in addresses[key]:
                msg = client.read_input_registers(address=address, count=2, slave=units[key])
                decoder = BinaryPayloadDecoder.fromRegisters(msg.registers, byteorder=Endian.BIG)
                match register_type[key]:
                    case 'int16':
                        return_value[key] += decoder.decode_16bit_int() * scales[key]
                    case 'uint16':
                        return_value[key] += decoder.decode_16bit_uint() * scales[key]
                    case _:
                        logger.error("format error %s", key)
                        return None
        client.close()
        logger.info("Victron read")
        return return_value

    except Exception as e:
        logger.error("Exception: %s", e)
        return None


if __name__ == "__main__":

    values = read_victron()
    if values:
        print(values)
