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
from utiles import from_bson, get_filled_only, is_bson_id

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


def check_permission(current_user: dict, target_role: Roles):
    if target_role == Roles.EMPLOYER:
        return
    if current_user[schemes.User.ROLE] != target_role:
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




# ALL BASC actions add/update/delete(soft)/read one_by_id or many
@project_route.get('/all')
async def get_all_projects(page: int = 1, current_user=Depends(get_current_user)):
    check_permission(current_user, Roles.ADMIN)
    start = (page - 1) * 15
    len_ = 15
    all_project_as_bson = await db.get_collection(Collections.PROJECT).find().skip(start).limit(len_).to_list(15)

    if len(all_project_as_bson) == 0:
        return []
    all_project_as_list = list(map(lambda item: from_bson(item, ProjectResponse), all_project_as_bson))
    return all_project_as_list


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


@project_route.post('/')
async def add_project(project_: Project, current_user: dict = Depends(get_current_user)):
    check_permission(current_user, Roles.ADMIN)
    json_format = project_.model_dump()
    json_format.update({'create_at: ': datetime.datetime.now()})
    json_format.update({'update_at': datetime.datetime.now()})
    id_ = await db.get_collection(Collections.PROJECT).insert_one(json_format)
    bson_return = await db.get_collection(Collections.PROJECT).find_one({'_id': ObjectId(id_.inserted_id)})
    return from_bson(bson_return, ProjectResponse)


@project_route.put('/')
async def update_project(project_update_model: ProjectUpdate, current_user: dict = Depends(get_current_user)):
    check_permission(current_user, Roles.ADMIN)
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
    return state


@project_route.delete('/{id_pro}')
async def delete_project(id_proj: str, current_user: dict = Depends(get_current_user)):
    check_permission(current_user, Roles.ADMIN)
    is_bson_id(id_proj)
    res_ = await db.get_collection(Collections.PROJECT).update_one({'_id': ObjectId(id_proj)},
                                                                   {'$set': {schemes.Project.IS_ACTIVE: False}})

    return {'state': 'project deleted successfully'}


# ADVANCED OPERATIONS
@project_route.get('/department/{id_dep}', tags=['department related object'])
async def get_project_department(id_dep: int, page: int=1, current_user: dict = Depends(get_current_user)):
    check_for_contributed_resources(current_user, id_dep)
    page = (page - 1) * 15
    len_ = 15
    department_ = await db.get_collection(Collections.DEPARTMENT).find_one(
        {schemes.DepartmentS.DEPARTMENT_IDENTIFICATION: id_dep})

    if department_ is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'No Department Found With Identifier {id_dep}'
        )
    data_ = await db.get_collection(Collections.PROJECT).find({schemes.Project.DEPARTMENT_ID: id_dep}).skip(page).limit(
        len_).to_list(len_)
    if len(data_) == 0:
        return []
    python_data = list(map(lambda item: from_bson(item, ProjectResponse), data_))
    return python_data


# FREQUENTLY ACTIONS : this and the function update are the same but for bandwidth and complexity raison with have separated them!

@project_route.put('frequently-actions', tags=['update frequently action'])
async def update_frequently(update_fa_model: ProjectFU, current_user: dict = Depends(get_current_user)):
    check_permission(current_user, Roles.D_MANAGER)
    data_ = update_fa_model.model_dump(by_alias=True)
    data_ = get_filled_only(data_)
    id_ = data_.pop('_id')
    is_bson_id(id_)
    project_ = await db.get_collection(Collections.PROJECT).find_one({'_id': ObjectId(id_)})

    check_for_contributed_resources(current_user, project_[schemes.Project.DEPARTMENT_ID]) # check whether the manager and the project in the same department
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
    return state