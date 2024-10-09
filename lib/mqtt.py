import paho.mqtt.client as mqtt
import paho.mqtt.subscribe as subscribe
import logging
import time

BROKER = "localhost"
STATE_PREFIX = "power_state/"
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
COMMAND_TOPICS = ["power_command/solar2heat",
                  "power_command/solar2car",
                  "power_command/charger_setpoint",
                  "power_command/charging"]


def on_message(client, userdata, message):
    """Message callback for testing."""
    print("message received " ,str(message.payload.decode("utf-8")))
    print("message topic=",message.topic)
    print("message qos=",message.qos)
    print("message retain flag=",message.retain)
    payload = str(message.payload.decode("utf-8"))
    print(payload)


def mqtt_init(broker = BROKER, callback = on_message):
    """Initialize the client"""
    client.on_message=on_message
    client.connect(broker)
    client.loop_start()
    for topic in COMMAND_TOPICS:
        client.subscribe(topic)


def mqtt_publish(data):
    """Publish a dict on mqtt"""
    for key, value in data.items():
        client.publish(STATE_PREFIX + key, value)


if __name__ == "__main__":
    logging.basicConfig(level=0)

    all_data = {
    'criticial_loads_power':    -88,
    'charger_power':            -99}

    print(all_data)
    mqtt_init(broker = "whiplash.fritz.box", callback = on_message)
    mqtt_publish(all_data)

    time.sleep(60)
    print("done.")

