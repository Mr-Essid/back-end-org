import datetime
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends
from starlette import status
import schemes
from database_config.Collections import Collections
from model.Employer import Roles
from .login_route import get_current_user
from database_config.configdb import db
from model.Project import Project, ProjectResponse, ProjectUpdate, ProjectFU
from utiles import from_bson, get_filled_only, is_bson_id, Admin_only, Employer_access, Admin_Department_manager, \
    Department_Manager_only
from MQTTFastAPI import fast_mqtt

project_route = APIRouter(prefix='/project')

"""
    model actions:
    CRUD:
        simple actions, delete it's just soft delete
    O.Action:
        add_progress frequently change
        change_current_state ( planing, implementing, testing )
        is_working_on
"""

"""
    in the project model there is privacy for project project except for the root user it mean
    
    get_all_project: only the root
    get_projects_of_department: root or employers department
    get_project_by_id: root or employers who contribute to it.
    
    add_project: only root
    update_project: only root
    delete(soft) : only root
    
    frq_updates:  only department manger of the department contribute in this project
    
"""


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


@project_route.get('/')
async def sendMqttMessage():
    fast_mqtt.publish('/ok', 'ok from project')


# ALL BASC actions add/update/delete(soft)/read one_by_id or many
@project_route.get('/all', )
async def get_all_projects(page: int = 1, is_working_on=False, current_user=Depends(get_current_user)):
    check_permission(current_user, [Roles.ADMIN])
    start = (page - 1) * 15
    len_ = 15

    query = {}

    if is_working_on:
        query.update({schemes.Project.IS_WORKING_ON: True})

    # get first latest updated ones
    all_project_as_bson = await db.get_collection(Collections.PROJECT).find(query).sort(
        {schemes.Project.END_AT: 1, schemes.Project.UPDATE_AT: -1, schemes.Project.CREATE_AT: -1}).skip(start).limit(
        len_).to_list(15)

    if len(all_project_as_bson) == 0:
        return []
    all_project_as_list = list(map(lambda item: from_bson(item, ProjectResponse), all_project_as_bson))
    return all_project_as_list


@project_route.get('/current_employer')
async def get_projects_of_current_user(page: int = 1, all_working_one: bool = False,
                                       current_user: dict = Depends(get_current_user)):
    page = (page - 1) * 15
    department_id_of_current_user = current_user.get(schemes.User.ID_DEPARTMENT)
    query = {
        schemes.Project.DEPARTMENT_ID: department_id_of_current_user,
        schemes.Project.IS_ACTIVE: True
    }

    if all_working_one:
        query.update({
            schemes.Project.IS_WORKING_ON: True
        })

    sort = {
        schemes.Project.END_AT: 1,
        schemes.Project.UPDATE_AT: -1,
        schemes.Project.CREATE_AT: -1
    }

    list_of_all_projects_of_user_sorted = await db.get_collection(Collections.PROJECT).find(query).sort(sort).skip(
        page).limit(15).to_list(15)
    list_of_pydantic = list(map(lambda item: from_bson(item, ProjectResponse), list_of_all_projects_of_user_sorted))

    return list_of_pydantic


@project_route.get('/{id_project}')
async def get_project_by_id(id_project: str, current_user: dict = Depends(get_current_user)):
    is_bson_id(id_project)
    bson_id = ObjectId(id_project)
    project_as_bison = await db.get_collection(Collections.PROJECT).find_one({'_id': bson_id})

    if project_as_bison is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Projects With ID {id_project}"
        )
    check_for_contributed_resources(current_user, project_as_bison[schemes.Project.DEPARTMENT_ID])

    return from_bson(project_as_bison, ProjectResponse)


@project_route.put('/')
async def update_project(project_update_model: ProjectUpdate, current_user: dict = Depends(get_current_user)):
    check_permission(current_user, [Roles.ADMIN])
    data_ = project_update_model.model_dump(by_alias=True)
    data_ = get_filled_only(data_)
    id_ = data_.pop('_id')
    is_bson_id(id_)
    if not ObjectId.is_valid(id_):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='wrong id_'
        )
    res_ = await db.get_collection(Collections.PROJECT).update_one({'_id': ObjectId(id_)}, {'$set': data_})
    modified = res_.modified_count

    state = {
        'state': 'project updated successfully'
    }

    if modified == 0:
        state.update({'state': 'no thing have been changed'})
    else:
        project_after_update = await db.get_collection(Collections.PROJECT).find_one({'_id': ObjectId(id_)})
        state.update({'new_': from_bson(project_after_update, ProjectResponse)})
        fast_mqtt.publish(f"/project/update/{current_user.get(schemes.User.ID_DEPARTMENT)}", project_update_model.id_)
    return state


@project_route.delete('/{id_proj}', tags=Admin_only)
async def delete_project(id_proj: str, current_user: dict = Depends(get_current_user)):
    check_permission(current_user, [Roles.ADMIN])
    is_bson_id(id_proj)

    res_ = await db.get_collection(Collections.PROJECT).update_one({'_id': ObjectId(id_proj)},
                                                                   {'$set': {schemes.Project.IS_ACTIVE: False}})

    return {'state': 'project deleted successfully'}


# ADVANCED OPERATIONS
@project_route.get('/department/{id_dep}')
async def get_project_department(id_dep: int, working_on_only: bool = False, page: int = 1,
                                 current_user: dict = Depends(get_current_user)):
    check_for_contributed_resources(current_user, id_dep)
    page = (page - 1) * 15
    len_ = 15
    department_ = await db.get_collection(Collections.DEPARTMENT).find_one(
        {schemes.DepartmentS.DEPARTMENT_IDENTIFICATION: id_dep})

    query = {schemes.Project.DEPARTMENT_ID: id_dep}

    if working_on_only:
        query.update({schemes.Project.IS_WORKING_ON: True})

    if department_ is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'No Department Found With Identifier {id_dep}'
        )
    data_ = await db.get_collection(Collections.PROJECT).find(query).sort(
        {schemes.Project.END_AT: 1, schemes.Project.UPDATE_AT: -1, schemes.Project.CREATE_AT: -1}).skip(page).limit(
        len_).to_list(len_)
    if len(data_) == 0:
        return []
    python_data = list(map(lambda item: from_bson(item, ProjectResponse), data_))
    return python_data


# FREQUENTLY ACTIONS : this and the function update are the same but for bandwidth and complexity raison with have separated them!


@project_route.put('frequently-actions', tags=Department_Manager_only)
async def update_frequently(update_fa_model: ProjectFU, current_user: dict = Depends(get_current_user)):
    check_permission(current_user, [Roles.D_MANAGER])
    data_ = update_fa_model.model_dump(by_alias=True)
    data_ = get_filled_only(data_)
    data_.update({schemes.Project.UPDATE_AT: datetime.datetime.now()})
    id_ = data_.pop('_id')
    is_bson_id(id_)
    project_ = await db.get_collection(Collections.PROJECT).find_one({'_id': ObjectId(id_)})
    check_for_contributed_resources(current_user, project_[
        schemes.Project.DEPARTMENT_ID])  # check whether the manager and the project in the same department
    res_ = await db.get_collection(Collections.PROJECT).update_one({'_id': ObjectId(id_)}, {'$set': data_})
    modified = res_.modified_count
    state = {
        'state': 'project updated successfully'
    }

    if modified == 0:
        state.update({'state': 'no thing have been changed'})

    else:
        project_after_update = await db.get_collection(Collections.PROJECT).find_one({'_id': ObjectId(id_)})
        state.update({'new_': from_bson(project_after_update, ProjectResponse)})
        fast_mqtt.publish(f'/project/update/{project_.get(schemes.Project.DEPARTMENT_ID)}', id_)

    return state
