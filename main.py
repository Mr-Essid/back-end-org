import time
import os
from datetime import datetime
from typing import Annotated

import pytz
from bson import ObjectId
from fastapi import FastAPI, Request, HTTPException, Depends, Form
from apscheduler.schedulers.background import BackgroundScheduler
from gmqtt import Client
from starlette import status

from starlette.staticfiles import StaticFiles
from MQTTFastAPI import fast_mqtt
import schemes
from database_config.Collections import Collections
from model import Project
from model.Employer import Roles, EmployerResponse
from model.History import HistoryDepartment, HistorySecure
from model.Project import ProjectResponse, ProjectFU
from model.Session import SessionRequest, SessionResponseAfter, SessionState
from route.employer_routes import employer_route
from route.history_route import history_route
from route.login_route import login_route, get_current_user
from route.message_route import messageRoute
from route.project_route import project_route
from route.department_route import department_route
from route.session_route import sessionRoutes, check_permission, check_for_contributed_resources
from cryptography.fernet import Fernet
from database_config.configdb import Database, db
from SocketIOServer import socket_io_app
from admin_routes.admin_controller import admin_route, getCurrentAdmin
import uvicorn
import aiofiles

from schemes import HistoryDepartmentS, HistorySecureS
from utiles import from_bson, is_bson_id, get_filled_only, Department_Manager_only, Admin_only, string_validate

API_KEY = 'RASPBERRYPI_API_KEY'
CRYPTO_KEY = 'RASPBERRYPI_CRYPTO_KEY'
CRYPTO_KEY_RASPBERRYPI = os.getenv(CRYPTO_KEY)

app = FastAPI()
fast_mqtt.init_app(app)


@fast_mqtt.on_disconnect()
def disconnect(client, flags):
    print('client disconnected')

    print("Connected: ", client, flags)


@fast_mqtt.on_connect()
def connect(client, flags, rc, properties):
    # test message
    fast_mqtt.client.subscribe("/get_secure_key")
    fast_mqtt.client.subscribe("/ok")
    fast_mqtt.publish('/ok', 'okkkk')
    print("Connected: ", client, flags, rc, properties)


@fast_mqtt.on_subscribe()
def subscribe(client: Client, mid: int, qos: int, properties):
    print(client.is_connected)
    print("subscribed", client, mid, qos, properties)


@fast_mqtt.on_message()
async def message(client, topic, payload, qof, properties):
    if topic == '/get_secure_key':
        with open('./crypto.key', 'rb') as file:
            key_to_publish = file.read().decode('utf-8', 'ignore')
            fernet_en_key = CRYPTO_KEY_RASPBERRYPI.encode()
            data_encrypted = encrypt_api_key(key_to_publish, fernet_en_key)
            fast_mqtt.publish('/crypto_api_key', payload=data_encrypted.decode())


@app.on_event("startup")
async def startup_event():
    scheduler = BackgroundScheduler()
    scheduler.add_job(crypt_synchronize, "interval", minutes=10)  # update the key every 10m
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

    fernet_en_key = CRYPTO_KEY_RASPBERRYPI.encode()
    data_encrypted = encrypt_api_key(RASPBERRYPI_KEY, fernet_en_key)

    try:
        fast_mqtt.publish('/crypto_api_key', payload=data_encrypted.decode())
        print('job done')
    except Exception as e:  # I haven't seen the error and there is no indicator for in the doc, so it's Exception
        print('client fchel')
        pass

    # IF ALL WORK FINE WE WILL MODIFY THE KEY IN OUR SIDE mqtt will try to reconnect automatically
    with open('crypto.key', 'wb') as file:
        file.write(new_key.encode())

    print('job done')


async def check_permission_pi(api_key: str):
    async with aiofiles.open('crypto.key', 'rb') as file:
        key_ = await file.read()

    if not api_key:
        raise HTTPException(
            detail="Request Not Permitted",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    key_s = api_key.split(" ")
    if len(key_s) < 2 or key_s[0] != 'Bearer' or key_s[1] != key_.decode('utf-8', 'ignore'):
        raise HTTPException(
            detail="request not permitted",
            status_code=status.HTTP_401_UNAUTHORIZED
        )


# end crypto part

# we need raspberrypi history register here cause of api key

@history_route.post('/department')
async def add_department_history(history_dep_model: HistoryDepartment, request: Request):
    is_bson_id(history_dep_model.employer_id)
    api_key = request.headers.get('Authorization')
    await check_permission_pi(api_key)
    data = history_dep_model.model_dump()
    current_date_time = datetime.now(tz=pytz.timezone('Europe/Jersey'))
    data[HistoryDepartmentS.DATE_TIME] = current_date_time

    inserted_id = await db.get_collection(Collections.HISTORY_DEPARTMENT).insert_one(
        data)  # this is the only await should be executed

    fast_mqtt.publish(f'/history/dep/{history_dep_model.employer_id}',
                      str(datetime.now(tz=pytz.timezone('Europe/Jersey'))))

    fast_mqtt.publish(f'/history/depID',
                      str(history_dep_model.department_id))

    return {'status': f'history inserted {str(inserted_id.inserted_id)}'}



@history_route.post('/secure')
async def add_secure_history(history_secure_model: HistorySecure, request: Request):
    api_key: str = request.headers.get('Authorization')
    await check_permission_pi(api_key)
    data = history_secure_model.model_dump()
    current_date_time = datetime.now(tz=pytz.timezone('Europe/Jersey'))
    data[HistorySecureS.DATE_TIME] = current_date_time
    inserted_id = await db.get_collection(Collections.HISTORY_SECURE).insert_one(
        data)  # this is the only await should be executed

    fast_mqtt.publish('/history/secure', history_secure_model.manager_id)
    return {'status': f'history inserted {str(inserted_id.inserted_id)}'}


@employer_route.get('/departments_/pi/{id_depart}', tags=['pi only request'])
async def employers_of_department_for_pi(id_depart: int, request: Request):
    api_key: str = request.headers.get('Authorization')
    await check_permission_pi(api_key)
    list_employers_ = await db.get_collection(Collections.USER).find(
        {schemes.User.ID_DEPARTMENT: id_depart}).to_list(None)
    if len(list_employers_) == 0:
        return []

    list_python_ = list(map(lambda item: from_bson(item, EmployerResponse), list_employers_))
    return list_python_


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@sessionRoutes.post('/')
async def addSession(sessionRequest: SessionRequest, current_user=Depends(get_current_user)):
    check_permission(current_user, [Roles.D_MANAGER, Roles.ADMIN])
    date_format = '%Y-%m-%dT%H:%M:%S'
    print(sessionRequest.model_dump(by_alias=True))
    begin_at = sessionRequest.beginAt.strftime(date_format)  # date of session
    estimated_time = sessionRequest.estimatedTimeInHours
    current_date = datetime.now(tz=pytz.timezone('Europe/Jersey')).strftime(date_format.split('T')[0])

    if begin_at < current_date or estimated_time < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="you have error in your input check your begin at time or eTime at least one hour"
        )
    department_id = current_user.get(schemes.User.ID_DEPARTMENT)
    department_ep = 'NC'  # Not Connected XD
    updated_at = datetime.now(tz=pytz.timezone('Europe/Jersey'))
    created_at = datetime.now(tz=pytz.timezone('Europe/Jersey'))
    dict_of_session = sessionRequest.model_dump(by_alias=True)
    dict_of_session.update({schemes.Session.D_ID: department_id})
    dict_of_session.update({schemes.Session.D_EP: department_ep})
    dict_of_session.update({schemes.Session.IS_DONE: False})
    dict_of_session.update({schemes.Session.MD_ID: current_user[schemes.User.ID_]})
    dict_of_session.update({schemes.Session.CREATED_AT: created_at})
    dict_of_session.update({schemes.Session.UPDATED_AT: updated_at})

    if begin_at.split("T")[0] != current_date.split("T")[0]:
        dict_of_session.update({schemes.Session.ISALIVE: False})

    if not dict_of_session.get(schemes.Session.ISONLINE):
        dict_of_session.update({schemes.Session.ISALIVE: False})

    if dict_of_session.get(schemes.Session.ISALIVE):
        dict_of_session.update({schemes.Session.IS_DONE: True})
        await db.get_collection(Collections.SESSION).update_many({schemes.Session.D_ID: department_id},
                                                                 {'$set': {
                                                                     schemes.Session.ISALIVE: False}})  # if we have an active session we will get off all of them

        fast_mqtt.publish(f'/session/{current_user.get(schemes.User.ID_DEPARTMENT)}',
                          'has been activated'.encode())  # all department members will notify

    id_inserted = await db.get_collection(Collections.SESSION).insert_one(dict_of_session)
    new_session_data = await db.get_collection(Collections.SESSION).find_one(
        {schemes.Session.ID_: id_inserted.inserted_id})

    return from_bson(new_session_data, SessionResponseAfter)


# project actions


@project_route.post('/', tags=Admin_only)
async def add_project(project_: Project.Project, current_user: dict = Depends(get_current_user)):
    check_permission(current_user, [Roles.ADMIN])
    json_format = project_.model_dump()
    if project_.department_identification not in [1, 2, 3]:  # currently those all department ids
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bad Department id"
        )
    json_format.update({'create_at: ': datetime.now(tz=pytz.timezone('Europe/Jersey'))})
    json_format.update({'update_at': datetime.now(tz=pytz.timezone('Europe/Jersey'))})
    id_ = await db.get_collection(Collections.PROJECT).insert_one(json_format)
    bson_return = await db.get_collection(Collections.PROJECT).find_one({'_id': ObjectId(id_.inserted_id)})
    fast_mqtt.publish(f'/project/add/{project_.department_identification}', str(id_.inserted_id).encode())
    return from_bson(bson_return, ProjectResponse)


@app.get('/')
async def main_route():
    list_of_users = await db.list_collection_names()
    fast_mqtt.publish(f'/session/',
                      'has been activated'.encode())
    return list_of_users



app.include_router(router=employer_route, tags=['Employer Actions'])
app.include_router(router=login_route, tags=['Login'])
app.include_router(router=department_route, tags=['Department Actions'])
app.include_router(router=project_route, tags=['Project Actions'])
app.include_router(router=history_route, tags=['History Actions'])
app.include_router(router=sessionRoutes, tags=['Session Actions'])
app.include_router(router=messageRoute, tags=['Message Actions'])
app.include_router(router=admin_route, tags=['Admin'])
app.mount("/static", StaticFiles(directory="./templates/static"), name="static")
app.mount('/', socket_io_app)

if __name__ == '__main__':
    uvicorn.run("main:app", host="0.0.0.0", port=8008, reload=True)
