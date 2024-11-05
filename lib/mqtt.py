"""mqtt to openhab interface"""
import logging
import time
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

BROKER = "localhost"
STATE_PREFIX = "power_state/"
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
COMMAND_TOPIC_PREFIX = "power_command/"
COMMAND_TOPICS = [COMMAND_TOPIC_PREFIX + "solar2heat",
                  COMMAND_TOPIC_PREFIX + "solar2car",
                  COMMAND_TOPIC_PREFIX + "charger_setpoint",
                  COMMAND_TOPIC_PREFIX + "charging"]


def callback0(client, userdata, message):
    """Message callback for testing."""
    print("message received " ,str(message.payload.decode("utf-8")))
    print("message topic=",message.topic)
    print("message qos=",message.qos)
    print("message retain flag=",message.retain)
    payload = str(message.payload.decode("utf-8"))
    print(payload)

def callback1(client, userdata, message):
    """Message callback for testing."""
    print("message received " ,str(message.payload.decode("utf-8")))
    print("message topic=",message.topic)
    print("message qos=",message.qos)
    print("message retain flag=",message.retain)
    payload = str(message.payload.decode("utf-8"))
    print(payload)

def callback2(client, userdata, message):
    """Message callback for testing."""
    print("message received " ,str(message.payload.decode("utf-8")))
    print("message topic=",message.topic)
    print("message qos=",message.qos)
    print("message retain flag=",message.retain)
    payload = str(message.payload.decode("utf-8"))
    print(payload)

def callback3(client, userdata, message):
    """Message callback for testing."""
    print("message received " ,str(message.payload.decode("utf-8")))
    print("message topic=",message.topic)
    print("message qos=",message.qos)
    print("message retain flag=",message.retain)
    payload = str(message.payload.decode("utf-8"))
    print(payload)

def mqtt_init(topics, callbacks, broker = BROKER):
    """Initialize the client"""
    client.connect(broker)
    client.on_message = callback0
    for topic, callback in zip(topics, callbacks):
        client.subscribe(topic)
        client.message_callback_add(topic, callback)
    client.loop_start()
    logger.info('mqtt client initialized.')

def mqtt_stop():
    """Initialize the client"""
    client.loop_stop()
    logger.info('mqtt client stopped.')


def mqtt_publish(data):
    """Publish a dict on mqtt"""
    for key, value in data.items():
        client.publish(STATE_PREFIX + key, value)
        logger.debug("publish: %s%s / %s", STATE_PREFIX, key, str(value))
    logger.info('mqtt_publish done.')


if __name__ == "__main__":
    logging.basicConfig(level=0)

    all_data = {
    'criticial_loads_power':    -88,
    'charger_power':            -99}

    print(all_data)
    mqtt_init(COMMAND_TOPICS, [callback0, callback1, callback2, callback3], broker = "whiplash.fritz.box")
    mqtt_publish(all_data)

    time.sleep(60)
    mqtt_stop()
    print("done.")

