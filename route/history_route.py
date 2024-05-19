import datetime
from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, Cookie, HTTPException, Request, status, Depends

from JWTUtilits import decodeAccessToken
from admin_routes.admin_controller import getCurrentAdmin
import schemes
from database_config.Collections import Collections
from model.Employer import Roles
from model.History import HistoryDepartment, HistorySecure, CountDateHistory
from schemes import HistoryDepartmentS, HistorySecureS
from database_config.configdb import db
from utiles import from_bson, is_bson_id
from .login_route import get_current_user

history_route = APIRouter(prefix='/history')

"""
    as I said before there is no update in the  history, why we even need :!
    all raspberry pi action need to be as fast as possible cause of realtime constraint in the embedded systems    
"""


def check_permission_history(current_user: dict, target_roles: list[Roles]):
    if not current_user[schemes.User.ROLE] in target_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='request not permitted'
        )


def check_for_contributed_history(current_user: dict, history_id_employer: str):
    if current_user[schemes.User.ROLE] == Roles.ADMIN:
        return

    if current_user[schemes.User.ID_] != history_id_employer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='access forbidden for this resource'
        )


@history_route.get('/departments/current_user')
async def get_history_of_current_employer(page: int = 1, current_user: dict = Depends(get_current_user)):
    page = (page - 1) * 15
    id_user = current_user.get(schemes.User.ID_)

    query = {
        schemes.HistoryDepartmentS.EMPLOYER_ID: id_user
    }
    list_of_bson_object = await db.get_collection(Collections.HISTORY_DEPARTMENT).find(query).sort(
        {schemes.HistoryDepartmentS.DATE_TIME: -1}
    ).skip(page).limit(15).to_list(15)
    list_of_pydantic_objects = list(map(lambda item: from_bson(item, HistoryDepartment), list_of_bson_object))
    return list_of_pydantic_objects


@history_route.get('/departments/current_user/statistic_five_days')
async def get_history_of_employers_five_days_ago(current_user: dict = Depends(get_current_user)):
    id_user = current_user.get(schemes.User.ID_)
    print(id_user)
    print(type(id_user))
    list_of_bson_object = await db.get_collection(Collections.HISTORY_DEPARTMENT).aggregate([
        {'$match': {HistoryDepartmentS.EMPLOYER_ID: id_user}},
        {'$group': {'_id': {'$dateToString': {'format': "%Y-%m-%d", 'date': "$date_time"}}, 'count': {'$sum': 1}}},
        {'$sort': {'_id': -1}},
    ]).to_list(5)

    pydantic_list = list(map(lambda item: from_bson(item, CountDateHistory), list_of_bson_object))
    return pydantic_list


@history_route.get('/departments/current_user/statistic_latest_days/{department}')
async def get_history_of_employers_latest_days_ago(department: int, current_user: dict = Depends(getCurrentAdmin)):
    list_of_bson_object = await db.get_collection(Collections.HISTORY_DEPARTMENT).aggregate([
        {'$match': {HistoryDepartmentS.DEPARTMENT_ID: department}},
        {'$group': {'_id': {'$dateToString': {'format': "%Y-%m-%d", 'date': "$date_time"}}, 'count': {'$sum': 1}}},
        {'$sort': {'_id': -1}},
    ]).to_list(1)

    pydantic_list = list(map(lambda item: from_bson(item, CountDateHistory), list_of_bson_object))
    return pydantic_list


@history_route.get('/department/{department_id}')
async def get_history_of_department(department_id: int, page: int = 1, current_user: dict = Depends(get_current_user)):
    check_permission_history(current_user, [Roles.ADMIN])
    page = (page - 1) * 15
    list_with_objectId = await db.get_collection(Collections.HISTORY_DEPARTMENT).find(
        {HistoryDepartmentS.DEPARTMENT_ID: department_id}).sort({schemes.HistoryDepartmentS.DATE_TIME: -1}).skip(
        page).limit(15).to_list(15)
    list_without_objectId = list(map(lambda item: from_bson(item, HistoryDepartment), list_with_objectId))
    return list_without_objectId


@history_route.get('/secure')
async def get_history_secure(page: int = 1, current_user: dict = Depends(get_current_user)):
    check_permission_history(current_user, [Roles.ADMIN])
    page = (page - 1) * 15
    list_ = await db.get_collection(Collections.HISTORY_SECURE).find().sort(
        {schemes.HistorySecureS.DATE_TIME: -1}).skip(page).limit(15).to_list(
        15)  # this list has ObjectId !
    list_without_object_id = list(map(lambda item: from_bson(item, HistorySecure), list_))
    return list_without_object_id


@history_route.get('/departments/{employer_id}')
async def get_employer_history(employer_id: str, page: int = 1, current_user: dict = Depends(get_current_user)):
    check_for_contributed_history(current_user, employer_id)
    page = (page - 1) * 15
    is_bson_id(employer_id)
    list_with_object_id = await db.get_collection(Collections.HISTORY_DEPARTMENT).find(
        {HistoryDepartmentS.EMPLOYER_ID: employer_id}).sort({schemes.HistoryDepartmentS.DATE_TIME: - 1}).skip(
        page).limit(15).to_list(15)
    list_without_object_id = list(map(lambda item: from_bson(item, HistoryDepartment), list_with_object_id))
    return list_without_object_id


@history_route.get('/secure/{manager_id}')
async def get_manager_history(manager_id: str, page: int = 1, current_user: dict = Depends(get_current_user)):
    check_permission_history(current_user, [Roles.ADMIN])
    is_bson_id(manager_id)
    page = (page - 1) * 15
    list_with_object_id = await db.get_collection(Collections.HISTORY_SECURE).find(
        {HistorySecureS.MANAGER_ID: manager_id}).sort({schemes.HistorySecureS.DATE_TIME: -1}).skip(page).limit(
        15).to_list(15)
    list_without_object_id = list(map(lambda item: from_bson(item, HistorySecure), list_with_object_id))
    return list_without_object_id


@history_route.get("/date")
async def get_history_by_date(required_date: datetime.datetime, current_user=Depends(get_current_user)):
    id_ = current_user.get(schemes.User.ID_)

    start_date = required_date.replace(hour=0, second=0, minute=0)
    end_date = required_date.replace(hour=23, second=59, minute=59)

    history_current_user_with_date = await db.get_collection(Collections.HISTORY_DEPARTMENT). \
        find(
        {schemes.HistoryDepartmentS.EMPLOYER_ID: id_,
         schemes.HistoryDepartmentS.DATE_TIME: {'$gt': start_date, '$lt': end_date}}). \
        to_list(None)

    pydantic_list = list(map(lambda item: from_bson(item, HistoryDepartment), history_current_user_with_date))

    return pydantic_list
