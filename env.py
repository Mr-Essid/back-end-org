from dotenv import load_dotenv
import os


def load_env():
    # CURRENT_WORKING_DIR = os.getcwd()
    # file_dotenv = os.path.join(CURRENT_WORKING_DIR, '.env')
    load_dotenv()
    USERNAME = os.getenv('USERNAME_')
    PASSWORD = os.getenv('PASSWORD')
    HOST = os.getenv('HOST')
    APP_NAME = os.getenv('APP_NAME')
    DATABASE_NAME = os.getenv('DATABASE_NAME')

    return USERNAME, PASSWORD, HOST, APP_NAME, DATABASE_NAME



def load_env_jwt():
    load_dotenv()
    return os.getenv('JWTKEY')

def load_smtp():
    load_dotenv()
    SMTP_HOST = os.getenv('SMTP_HOST')
    SMTP_USERNAME = os.getenv('SMTP_USERNAME')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    SMTP_FROM_MAIL = os.getenv('SMTP_FROM_MAIL')
    SMTP_MAIL_FROM_NAME = os.getenv('SMTP_MAIL_FROM_NAME')
    PORT = os.getenv('POST_SMTP')

    return SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM_MAIL,SMTP_MAIL_FROM_NAME, PORT


def load_mqtt():
    load_dotenv()
    HOST_MQTT=os.getenv('MQTT_HOST')
    PORT_MQTT=os.getenv('MQTT_PROT')
    USERNAME=os.getenv('MQTT_USERNAME')
    PASSWORD=os.getenv('MQTT_PASSWORD')
    return USERNAME, PASSWORD, HOST_MQTT, PORT_MQTT
