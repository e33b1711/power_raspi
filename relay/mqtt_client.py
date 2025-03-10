import paho.mqtt.client as mqtt
import ssl
from datetime import datetime as dt

def on_connect(client, userdata, flags, reason_code, properties=None):
    client.subscribe(topic="RXB")

def on_message(client, userdata, message, properties=None):
    print(
        f"{dt.now()} Received message {message.payload} on topic '{message.topic}' with QoS {message.qos}"
    )

def on_subscribe(client, userdata, mid, qos, properties=None):
    print(f"{dt.now()} Subscribed with QoS {qos}")


client = mqtt.Client(client_id="clientid", clean_session=True)
client.on_connect = on_connect
client.on_message = on_message
client.on_subscribe = on_subscribe
client.connect(host="ironmaiden", keepalive=60)
client.subscribe([("ard_state/#", 1), ("ard_command/#", 1)])
client.loop_forever()
