from fastapi_mqtt import FastMQTT, MQTTConfig

from env import load_mqtt

USERNAME_MQTT, PASSWORD_MQTT, HOST_MQTT, PORT_MQTT = load_mqtt()

mqtt_config = MQTTConfig(
    username=USERNAME_MQTT,
    password=PASSWORD_MQTT,
    host=HOST_MQTT,
    port=PORT_MQTT,
    ssl=True,
    will_message_topic="/disconnect",
    will_message_message="mqtt disconnect from server 0000",
    reconnect_retries=20

)

fast_mqtt = FastMQTT(config=mqtt_config)