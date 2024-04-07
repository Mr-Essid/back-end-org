import datetime

from bson import ObjectId
from fastapi import APIRouter, HTTPException, status
from database_config.Collections import Collections
from model.History import HistoryDepartment, HistorySecure
from schemes import HistoryDepartmentS, HistorySecureS
from database_config.configdb import db
from utiles import from_bson, is_bson_id

history_route = APIRouter(prefix='/history')

"""
    as I said before there is no update in the  history, why we even need :!
    all raspberry pi action need to be as fast as possible cause of realtime constraint in the embedded systems    
"""


@history_route.post('/department')
async def add_department_history(history_dep_model: HistoryDepartment):
    data = history_dep_model.model_dump()
    current_date_time = datetime.datetime.now()
    data[HistoryDepartmentS.DATE_TIME] = current_date_time
    inserted_id = await db.get_collection(Collections.HISTORY_DEPARTMENT).insert_one(
        data)  # this is the only await should be executed
    return {'status': f'history inserted {str(inserted_id.inserted_id)}'}


@history_route.post('/secure')
async def add_secure_history(history_secure_model: HistorySecure):
    data = history_secure_model.model_dump()
    current_date_time = datetime.datetime.now()
    data[HistorySecureS.DATE_TIME] = current_date_time
    inserted_id = await db.get_collection(Collections.HISTORY_SECURE).insert_one(
        data)  # this is the only await should be executed
    return {'status': f'history inserted {str(inserted_id.inserted_id)}'}


@history_route.get('/department/{department_id}')
async def get_history_of_department(department_id: int, page: int = 1):
    page = (page - 1) * 15
    list_with_objectId = await db.get_collection(Collections.HISTORY_DEPARTMENT).find(
        {HistoryDepartmentS.DEPARTMENT_ID: department_id}).skip(page).limit(15).to_list(15)
    list_without_objectId = list(map(lambda item: from_bson(item, HistoryDepartment), list_with_objectId))
    return list_without_objectId


@history_route.get('/secure')
async def get_history_secure(page: int = 1):
    page = (page - 1) * 15
    list_ = await db.get_collection(Collections.HISTORY_SECURE).find().skip(page).limit(15).to_list(
        15)  # this list has ObjectId !
    list_without_object_id = list(map(lambda item: from_bson(item, HistorySecure), list_))
    return list_without_object_id


@history_route.get('/departments/{employer_id}')
async def get_employer_history(employer_id: str, page: int = 1):
    page = (page - 1) * 15
    is_bson_id(employer_id)
    list_with_object_id = await db.get_collection(Collections.HISTORY_DEPARTMENT).find(
        {HistoryDepartmentS.EMPLOYER_ID: employer_id}).skip(page).limit(15).to_list(15)
    print(list_with_object_id)
    list_without_object_id = list(map(lambda item: from_bson(item, HistoryDepartment), list_with_object_id))
    return list_without_object_id


@history_route.get('/secure/{manager_id}')
async def get_manager_history(manager_id: str, page: int = 1):
    is_bson_id(manager_id)
    page = (page - 1) * 15
    list_with_object_id = await db.get_collection(Collections.HISTORY_SECURE).find(
        {HistorySecureS.MANAGER_ID: manager_id}).skip(page).limit(15).to_list(15)
    list_without_object_id = list(map(lambda item: from_bson(item, HistorySecure), list_with_object_id))
    return list_without_object_id
