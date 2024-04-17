import datetime

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends
from starlette import status
from model.Employer import Roles
from model.Session import SessionState, SessionResponseAfter, SessionRequest, SessionResponseBefore, SessionUpdate
from database_config.configdb import db
from database_config.Collections import Collections
from utiles import from_bson, is_bson_id, get_filled_only
import schemes
from .login_route import get_current_user

sessionRoutes = APIRouter(prefix='/session')


def check_permission(current_user: dict, target_roles: list[Roles]):
    if not current_user[schemes.User.ROLE] in target_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='request not permitted'
        )


def check_for_contributed_resources(current_user: dict, id_project_department: int):
    if current_user[schemes.User.ROLE] == Roles.ADMIN:
        return

    if current_user[schemes.User.ID_DEPARTMENT] != id_project_department:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='access forbidden for this resource'
        )


@sessionRoutes.get('/all')
async def getAllSessions(page: int = 1, current_user=Depends(get_current_user)):
    check_permission(current_user, target_roles=[Roles.ADMIN])
    page = (page - 1) * 15
    list_of_sessions = await db.get_collection(Collections.SESSION).find().skip(page).limit(15).to_list(15)
    list_python_model = list(map(lambda item: from_bson(item, SessionResponseAfter), list_of_sessions))
    return list_python_model


@sessionRoutes.get('/{id_}/session')
async def getSessionById(id_: str, current_user=Depends(get_current_user)):
    is_bson_id(id_)
    session_dict = await db.get_collection(Collections.SESSION).find_one({schemes.Session.ID_: ObjectId(id_)})
    if session_dict is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'No Session Found With ID {id_}'
        )
    check_for_contributed_resources(current_user, session_dict[schemes.Session.D_ID])
    return from_bson(session_dict, SessionResponseAfter)


@sessionRoutes.get('/sessions/current_user')
async def get_sessions_of_current_user(page: int = 1, current_user: dict = Depends(get_current_user)):
    id_dep_user = current_user.get(schemes.User.ID_DEPARTMENT)
    page = (page - 1) * 15
    sessionOfDep = await db.get_collection(Collections.SESSION).find({schemes.Session.D_ID: id_dep_user}).sort(
        {schemes.Session.ISALIVE: -1, schemes.Session.UPDATED_AT: -1, schemes.Session.CREATED_AT: -1}).skip(
        page).limit(
        15).to_list(15)
    listOfPython = list(map(lambda item: from_bson(item, SessionResponseAfter), sessionOfDep))
    return listOfPython


@sessionRoutes.get('/{department_id}/department')
async def getSessionOfDepartment(department_id: int, page: int = 1, current_user=Depends(get_current_user)):
    check_permission(current_user, target_roles=[Roles.ADMIN, Roles.D_MANAGER])
    check_for_contributed_resources(current_user, department_id)
    page = (page - 1) * 15
    sessionOfDep = await db.get_collection(Collections.SESSION).find({schemes.Session.D_ID: department_id}).skip(
        page).limit(
        15).to_list(15)
    listOfPython = list(map(lambda item: from_bson(item, SessionResponseAfter), sessionOfDep))
    return listOfPython


@sessionRoutes.get('/{project_id}/project')
async def getSessionsOfProject(project_id: str, page: int = 1, current_user=Depends(get_current_user)):
    is_bson_id(project_id)
    page = (page - 1) * 15

    project_in_question = await db.get_collection(Collections.PROJECT).find_one({schemes.Project.ID_: ObjectId(project_id)})

    if project_in_question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='project not exists'
        )

    check_for_contributed_resources(current_user, project_in_question[schemes.Project.DEPARTMENT_ID])

    sessionOfProj = await db.get_collection(Collections.SESSION).find({schemes.Session.PROJECT_ID: project_id}).skip(
        page).limit(15).to_list(15)

    listPython = list(map(lambda item: from_bson(item, SessionResponseAfter), sessionOfProj))
    return listPython


@sessionRoutes.post('/')
async def addSession(sessionRequest: SessionRequest, current_user=Depends(get_current_user)):
    check_permission(current_user, [Roles.D_MANAGER, Roles.ADMIN])
    date_format = '%Y-%m-%dT%H:%M:%S'
    print(sessionRequest.model_dump(by_alias=True))
    begin_at = sessionRequest.beginAt.strftime(date_format)  # date of session
    estimated_time = sessionRequest.estimatedTimeInHours
    current_date = datetime.datetime.now().strftime(date_format)

    if begin_at < current_date or estimated_time < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="you have error in your input check your begin at time or eTime at least one hour"
        )
    department_id = current_user.get(schemes.User.ID_DEPARTMENT)
    department_ep = 'NC'  # Not Connected XD
    updated_at = datetime.datetime.now()
    created_at = datetime.datetime.now()
    dict_of_session = sessionRequest.model_dump(by_alias=True)
    dict_of_session.update({schemes.Session.D_ID: department_id})
    dict_of_session.update({schemes.Session.D_EP: department_ep})
    dict_of_session.update({schemes.Session.MD_ID: current_user[schemes.User.ID_]})
    dict_of_session.update({schemes.Session.CREATED_AT: created_at})
    dict_of_session.update({schemes.Session.UPDATED_AT: updated_at})
    id_inserted = await db.get_collection(Collections.SESSION).insert_one(dict_of_session)
    new_session_data = await db.get_collection(Collections.SESSION).find_one(
        {schemes.Session.ID_: id_inserted.inserted_id})
    return from_bson(new_session_data, SessionResponseAfter)


@sessionRoutes.put('/')
async def updateSession(session_to_update: SessionUpdate, current_user=Depends(get_current_user)):
    check_permission(current_user, [Roles.D_MANAGER, Roles.ADMIN])

    session_: dict = await db.get_collection(Collections.SESSION).find_one(
        {schemes.Session.ID_: ObjectId(session_to_update.id_)})
    if session_ is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"session not found with id {session_to_update.id_}"
        )
    creator_id = session_.get(schemes.Session.MD_ID)
    check_for_contributed_resources(current_user, creator_id)
    session_dict = session_to_update.model_dump(by_alias=True)
    id_session = session_dict.pop(schemes.Session.ID_)
    session_dict = get_filled_only(session_dict)
    res_ = await db.get_collection(Collections.SESSION).update_one({schemes.Session.ID_: ObjectId(id_session)},
                                                                   {'$set': session_dict})
    new_session = await db.get_collection(Collections.SESSION).find_one({schemes.Session.ID_: ObjectId(id_session)})

    if res_.modified_count > 0:
        return {
            'state': 'session updated successfully',
            'session': from_bson(new_session, SessionResponseAfter)
        }

    return {
        'status': 'No change at All'
    }


@sessionRoutes.put('/active/{id_session}')
async def activeSession(id_session: str, activation_state: SessionState, current_user=Depends(get_current_user)):
    is_bson_id(id_session)
    session_on_question = await db.get_collection(Collections.SESSION).find_one(
        {schemes.Session.ID_: ObjectId(id_session)})

    if session_on_question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'No Session With Id {id_session}'
        )

    creator_id = session_on_question.get(schemes.Session.D_ID)
    check_for_contributed_resources(current_user, creator_id)
    if activation_state == SessionState.ACTIVE:
        await db.get_collection(Collections.SESSION).update_many(
            {schemes.Session.ISALIVE: True, schemes.Session.D_ID: session_on_question.get(schemes.Session.D_ID)},
            {'$set': {schemes.Session.ISALIVE: False}})  # terminate activated session while this one is alive

    query = {
        schemes.Session.ISALIVE: True
    }
    if activation_state == SessionState.DIS_ACTIVE:
        query.update({schemes.Session.ISALIVE: False})
        query.update({schemes.Session.UPDATED_AT: datetime.datetime.now()})

    res = await db.get_collection(Collections.SESSION).update_one({schemes.Session.ID_: ObjectId(id_session)},
                                                                  {'$set': query})

    return {
        'state': 'session activated successfully'
    } if res.modified_count > 0 else {
        'state': 'some things went wrong'
    }


@sessionRoutes.get('/last_host')
async def get_last_hot_session_cu(current_user: dict = Depends(get_current_user)):
    department_id = current_user.get(schemes.User.ID_DEPARTMENT)
    sort_ = {
        schemes.Session.ISALIVE: -1,
        schemes.Session.UPDATED_AT: -1,
        schemes.Session.CREATED_AT: -1,
    }
    latest_session_hot = await db.get_collection(Collections.SESSION).find({
        schemes.Session.D_ID: department_id
    }).sort(sort_).limit(1).to_list(1)

    from_bson_to_pydantic = list(map(lambda item: from_bson(item, SessionResponseAfter), latest_session_hot))

    return from_bson_to_pydantic[0] if len(from_bson_to_pydantic) > 0 else None
