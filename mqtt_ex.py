import paho.mqtt.client as mqtt
import time
import signal
import sys

broker_address      = "openhabianpi2.fritz.box"
state_topic         = "power_state/heat_control"
command_topic       = "power_command/heat_control"
client = mqtt.Client("P1")

def on_message(client, userdata, message):
    print("message received " ,str(message.payload.decode("utf-8")))
    print("message topic=",message.topic)
    print("message qos=",message.qos)
    print("message retain flag=",message.retain)
    client.publish(state_topic,str(message.payload.decode("utf-8")))

def signal_handler(sig, frame):
    client.loop_stop() 
    print('Exit...')
    sys.exit(0)


if __name__ == "__main__":

    signal.signal(signal.SIGINT, signal_handler)
    
    client.on_message=on_message
    client.connect(broker_address)
    client.loop_start() 
    client.subscribe(command_topic)
    
    while 1:
        #client.publish(state_topic,"OFF")
        #time.sleep(10)
        #client.publish(state_topic,"ON")
        time.sleep(10)