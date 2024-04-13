import time
import os
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from apscheduler.schedulers.background import BackgroundScheduler
from starlette import status
from database_config.Collections import Collections
from model.History import HistoryDepartment, HistorySecure
from route.employer_routes import employer_route
from route.history_route import history_route
from route.login_route import login_route
from route.project_route import project_route
from route.department_route import department_route
from route.session_route import sessionRoutes
from cryptography.fernet import Fernet
from database_config.configdb import Database, db
from fastapi_mqtt import FastMQTT
from fastapi_mqtt.config import MQTTConfig
from env import load_mqtt
from SocketIOServer import sio, socket_io_app
import uvicorn
import aiofiles

from schemes import HistoryDepartmentS, HistorySecureS

# @contextualisation
# async def lifespan(app: FastAPI):
#     scheduler = BackgroundScheduler()
#     scheduler.add_job(crypt_synchronize, "interval", minutes=30)
#     scheduler.start()
#     Database()
#     yield
#     scheduler.shutdown()
#     print('Bay')

API_KEY = 'RASPBERRYPI_API_KEY'
CRYPTO_KEY = 'RASPBERRYPI_CRYPTO_KEY'
CRYPTO_KEY_RASPBERRYPI = os.getenv(CRYPTO_KEY)
USERNAME_MQTT, PASSWORD_MQTT, HOST_MQTT, PORT_MQTT = load_mqtt()

app = FastAPI()
mqtt_config = MQTTConfig(
    username=USERNAME_MQTT,
    password=PASSWORD_MQTT,
    host=HOST_MQTT,
    port=PORT_MQTT,
    ssl=True
)


@app.on_event("startup")
async def startup_event():
    scheduler = BackgroundScheduler()
    scheduler.add_job(crypt_synchronize, "interval", minutes=30)
    scheduler.start()
    Database()

    print('all configurations are done')


# crypto part


def encrypt_api_key(api_key: str, key_: bytes):
    fernet_instance = Fernet(key_)
    encrypted_key = fernet_instance.encrypt(api_key.encode())
    return encrypted_key


def crypt_synchronize():
    new_key = os.urandom(32).hex()
    RASPBERRYPI_KEY = new_key  # this is our key
    # prepare it to send over mqtt crypt it
    print(new_key)
    with open('key.txt', 'w') as file:
        file.write(new_key)

    fernet_en_key = CRYPTO_KEY_RASPBERRYPI.encode()
    data_encrypted = encrypt_api_key(RASPBERRYPI_KEY, fernet_en_key)
    fast_mqtt.publish('/crypto_api_key', payload=data_encrypted.decode())
    print('job done')


async def check_permission_pi(api_key: str):
    async with aiofiles.open('key.txt', 'r') as file:
        key_ = await file.read()
    print(key_)
    if not api_key:
        raise HTTPException(
            detail="Request Not Permitted",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    key_s = api_key.split(" ")
    if len(key_s) < 2 or key_s[0] != 'Bearer' or key_s[1] != key_:
        raise HTTPException(
                detail="request not permitted",
                status_code=status.HTTP_401_UNAUTHORIZED
            )


# end crypto part

# we need raspberrypi history register here cause of api key

@history_route.post('/department')
async def add_department_history(history_dep_model: HistoryDepartment, request: Request):
    api_key = request.headers.get('Authorization')
    await check_permission_pi(api_key)
    data = history_dep_model.model_dump()
    current_date_time = datetime.now()
    data[HistoryDepartmentS.DATE_TIME] = current_date_time
    inserted_id = await db.get_collection(Collections.HISTORY_DEPARTMENT).insert_one(
        data)  # this is the only await should be executed
    return {'status': f'history inserted {str(inserted_id.inserted_id)}'}


@history_route.post('/secure')
async def add_secure_history(history_secure_model: HistorySecure, request: Request):
    api_key: str = request.headers.get('Authorization')
    await check_permission_pi(api_key)
    data = history_secure_model.model_dump()
    current_date_time = datetime.now()
    data[HistorySecureS.DATE_TIME] = current_date_time
    inserted_id = await db.get_collection(Collections.HISTORY_SECURE).insert_one(
        data)  # this is the only await should be executed
    return {'status': f'history inserted {str(inserted_id.inserted_id)}'}


fast_mqtt = FastMQTT(config=mqtt_config)
fast_mqtt.init_app(app)


@fast_mqtt.on_connect()
def connect(client, flags, rc, properties):
    fast_mqtt.client.subscribe("/mqtt")
    print("Connected: ", client, flags, rc, properties)


@fast_mqtt.on_message()
async def message(client, topic, payload, qof, properties):
    pass  # here we don't need any received message and thanks, please don't ask me why I put it because I love it ok !!!


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.get('/')
async def main_route():
    list_of_users = await db.list_collection_names()
    return list_of_users


app.include_router(router=employer_route, tags=['Employer Actions'])
app.include_router(router=login_route, tags=['Login'])
app.include_router(router=department_route, tags=['Department Actions'])
app.include_router(router=project_route, tags=['Project Actions'])
app.include_router(router=history_route, tags=['History Actions'])
app.include_router(router=sessionRoutes, tags=['Session Actions'])
app.mount('/', socket_io_app)


if __name__ == '__main__':
    uvicorn.run('main:app', reload=True)
