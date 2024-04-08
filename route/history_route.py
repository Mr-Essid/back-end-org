import datetime

from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Depends

import schemes
from database_config.Collections import Collections
from model.Employer import Roles
from model.History import HistoryDepartment, HistorySecure
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





@history_route.get('/department/{department_id}')
async def get_history_of_department(department_id: int, page: int = 1, current_user: dict = Depends(get_current_user)):
    check_permission_history(current_user, [Roles.ADMIN])
    page = (page - 1) * 15
    list_with_objectId = await db.get_collection(Collections.HISTORY_DEPARTMENT).find(
        {HistoryDepartmentS.DEPARTMENT_ID: department_id}).skip(page).limit(15).to_list(15)
    list_without_objectId = list(map(lambda item: from_bson(item, HistoryDepartment), list_with_objectId))
    return list_without_objectId


@history_route.get('/secure')
async def get_history_secure(page: int = 1, current_user: dict = Depends(get_current_user)):
    check_permission_history(current_user, [Roles.ADMIN])
    page = (page - 1) * 15
    list_ = await db.get_collection(Collections.HISTORY_SECURE).find().skip(page).limit(15).to_list(
        15)  # this list has ObjectId !
    list_without_object_id = list(map(lambda item: from_bson(item, HistorySecure), list_))
    return list_without_object_id


@history_route.get('/departments/{employer_id}')
async def get_employer_history(employer_id: str, page: int = 1, current_user: dict = Depends(get_current_user)):
    check_for_contributed_history(current_user, employer_id)
    page = (page - 1) * 15
    is_bson_id(employer_id)
    list_with_object_id = await db.get_collection(Collections.HISTORY_DEPARTMENT).find(
        {HistoryDepartmentS.EMPLOYER_ID: employer_id}).skip(page).limit(15).to_list(15)
    print(list_with_object_id)
    list_without_object_id = list(map(lambda item: from_bson(item, HistoryDepartment), list_with_object_id))
    return list_without_object_id


@history_route.get('/secure/{manager_id}')
async def get_manager_history(manager_id: str, page: int = 1, current_user: dict = Depends(get_current_user)):
    check_permission_history(current_user, [Roles.ADMIN])
    is_bson_id(manager_id)
    page = (page - 1) * 15
    list_with_object_id = await db.get_collection(Collections.HISTORY_SECURE).find(
        {HistorySecureS.MANAGER_ID: manager_id}).skip(page).limit(15).to_list(15)
    list_without_object_id = list(map(lambda item: from_bson(item, HistorySecure), list_with_object_id))
    return list_without_object_id
