#!/usr/bin/python3
import socket
import sys
import signal

import paho.mqtt.client as mqtt

#mqtt stuff
#state topics:  are just the dictonary names 
broker_address = "localhost"
mqtt_state_prefix = "ard_state/"
client = mqtt.Client("P25")

def on_message(client, userdata, message):
    print(message.topic, " ", str(message.payload.decode("utf-8")))
    topic = message.topic.split("/")
    print(topic)
    if topic[0]=="ard_command":
        echo = "!c!" + topic[1] + "!" + str(message.payload.decode("utf-8")) + "$\n"
        print(">>>" + echo)
        sock.send(echo.encode());
    
def publish_mqtt(key, payload):
    client.publish(mqtt_state_prefix + key, payload)
        
        

   

# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect the socket to the port where the server is listening
server_address = ('raspberrypi.fritz.box', 8888)
print ('connecting to %s port %s' % server_address)
sock.connect(server_address)


#message = 'This is the message.  It will be repeated.'
#print( 'sending "%s"' % message)
#sock.sendall(message)

def signal_handler(sig, frame):
    sock.close()
    
    print('Exit...')
    sys.exit(0)
    
if __name__ == "__main__":

    #mqtt
    client.on_message=on_message
    client.connect(broker_address)
    client.loop_start() 
    client.subscribe('ard_commmand/#')
    client.subscribe('ard_state/#')

    #gracefull strg+c
    signal.signal(signal.SIGINT, signal_handler)

    amount_received = 0

    message_complete=0
    message=''

    while 1:
        if not(message_complete):
            char = sock.recv(1)
            #print(char)
            if char==b'$':
                message_complete=1
            else:
                if char==b'\n':
                    message=''
                else:
                    message += char.decode('UTF-8')   
        else:
            print(message)
            message_complete=0
            sub_message = message.split("!")
            if len(sub_message)>=4:
                if sub_message[1]=="s":
                    publish_mqtt(sub_message[2], sub_message[3])
                    
            #print(sub_message)
                


    sock.close()
