#!/usr/bin/env python3

from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder



from paho.mqtt import client as mqtt_client
broker = 'openhabianpi2.fritz.box'
port = 1883
topic = "power_control/powerBal"
client_id = "raspi_power"


import logging
FORMAT = ('%(asctime)-15s %(threadName)-15s '
          '%(levelname)-8s %(module)-15s:%(lineno)-8s %(message)s')
logging.basicConfig(format=FORMAT)
log = logging.getLogger()
log.setLevel(logging.DEBUG)

UNIT = 0x1

import time


sdm630_info         = ["p1_power", "p2_power", "p3_power"]
sdm630_addresses    = [ 0x0C, 0x0E, 0x10]
sdm630_values       = [0, 0, 0]


def run_sync_client():

    client = ModbusClient(method='rtu', port='/dev/ttyUSB0', timeout=1, baudrate=9600)
    client.connect()

    
    for index in range(len(sdm630_info)):
        result =  client.read_input_registers(address=sdm630_addresses[index], count=2, unit=1)
    
        if result.isError():
            log.debug("Error reading " + sdm630_info[index])
        else:
            decoder = BinaryPayloadDecoder.fromRegisters(result.registers, wordorder=Endian.Big, byteorder=Endian.Big)
            sdm630_values[index] = decoder.decode_32bit_float()
            print(sdm630_info[index] + ": " + str(sdm630_values[index]))

    client.close()
    
    
def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)
    # Set Connecting Client ID
    client = mqtt_client.Client(client_id)
    #client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client
    
def publish(client):

         msg = str((sdm630_values[0] + sdm630_values[1] + sdm630_values[2])/3)
         result = client.publish(topic, msg)
         # result: [0, 1]
         status = result[0]
         if status == 0:
             print(f"Send `{msg}` to topic `{topic}`")
         else:
             print(f"Failed to send message to topic {topic}")


if __name__ == "__main__":

    client = connect_mqtt()
    client.loop_start()
    
    while 1:
        run_sync_client()
        publish(client)
        time.sleep(10)
        
        
        
        
        
        
