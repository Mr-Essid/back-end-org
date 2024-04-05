from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends
from starlette import status

from Authorities import Authorities
from database_config.Collections import Collections
from database_config.configdb import db
from model.Departement import Department
from schemes import DepartmentS, User
from utiles import from_bson
from .login_route import get_current_user

department_route = APIRouter(prefix='/department')


@department_route.get('/departments')
async def get_all_depart():
    list_departments = await db.get_collection(Collections.DEPARTMENT).find().to_list(5)
    list_dep_pars = list(map(lambda item: from_bson(item, Department), list_departments))
    return list_dep_pars


@department_route.post('/departments')
async def add_depart(department_data: Department, current_user=Depends(get_current_user)):
    if current_user[User.AUTHORITIES] != Authorities.ROOT:
        raise ValueError('request not permitted')

    department_data = department_data.model_dump()
    res = await db.get_collection(Collections.DEPARTMENT).insert_one(department_data)
    res_ = await db.get_collection(Collections.DEPARTMENT).find_one({'_id': ObjectId(res.inserted_id)})
    return from_bson(res_, Department)


@department_route.get('/department/{id_dep}')
async def get_department_by_id(id_dep: int):
    department_ = await db.get_collection(Collections.DEPARTMENT).find_one(
        {DepartmentS.DEPARTMENT_IDENTIFICATION: id_dep})

    if department_ is None:
        raise HTTPException(
            detail=f'Department With Id {id_dep} Not Found',
            status_code=status.HTTP_404_NOT_FOUND
        )

    return from_bson(department_, Department)
