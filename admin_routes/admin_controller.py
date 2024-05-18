import json
import re
from typing import Annotated

import bson
from bson import ObjectId
from fastapi import APIRouter, Depends, Cookie, Form, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from jose import ExpiredSignatureError, JWTError
from jose.exceptions import JWTClaimsError
import pymongo
import pymongo.errors
import pytz
from starlette.requests import Request
import datetime
from cryptography.fernet import Fernet

from env import load_mqtt
from model import Employer
from model.Departement import Department
from model.History import CountDateHistory, HistorySecureResponse
import model.History
from schemes import DepartmentS, HistoryDepartmentS, HistorySecureS, Project
import model.Project
from JWTUtilits import create_access_token, decodeAccessToken
from database_config.Collections import Collections
from database_config.configdb import db
from model.Employer import Roles
from schemes import User
from utiles import check_username, crypt_pass, from_bson, is_bson_id, string_validate, transfom_date, verify_password
from MQTTFastAPI import fast_mqtt

admin_route = APIRouter(prefix='/admin')

templates = Jinja2Templates("templates")

USERNAME_MQTT, PASSWORD_MQTT, HOST_MQTT, PORT_MQTT = load_mqtt()


def getCurrentAdmin(request: Request, session_id: Annotated[str | None, Cookie()] = None):
    print('this callback called')

    try:
        token = decodeAccessToken(session_id)
        email = token.get('sub')
        username = token.get('username')
        role = token.get('role')
        return True, {
            User.FULL_NAME: username,
            User.EMAIL: email,
            User.ROLE: role
        }
    except (ExpiredSignatureError, JWTError, JWTClaimsError, AttributeError) as e:
        if type(e) is ExpiredSignatureError:
            return False, {
                'status': 'token-exprired'
            }
        elif e is AttributeError:
            return False, {
                'status': 'token-not-exits'
            }
        else:
            return False, {
                'status': 'invalid-token'

            }


@admin_route.get('/login', name='login')
def loginGet(request: Request):
    return templates.TemplateResponse(name="index.html", request=request)


@admin_route.post('/dashboard', name='dashboard')
async def loginPost(request: Request, response: Response, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    root: dict = await db.get_collection(Collections.USER).find_one({'email': form_data.username})
    redirect_path = request.url_for("login").__str__() + '?x-error=invalid-cridentiels'

    redirect_object = RedirectResponse(
        url=redirect_path,
        status_code=status.HTTP_302_FOUND,
        headers={
            'x-error': 'invalid-cridentiels'
        })
    if root is None:
        return redirect_object
    password = root.get('password')

    if not verify_password(form_data.password, password):
        return redirect_object

    if root.get('role') != Roles.ADMIN:
        return redirect_object

    data = {'sub': root.get('email'), 'username': root.get('full_name'), 'role': root.get('role')}

    token = create_access_token(data, expires_delta=datetime.timedelta(hours=3))

    redirect = RedirectResponse(request.url_for('dashboard_get'), status_code=status.HTTP_302_FOUND)
    redirect.set_cookie("session_id", token)

    return redirect


@admin_route.get('/dashboard', name='dashboard_get')
async def main_dashboard(request: Request, current_admin: Annotated[tuple | None, Depends(getCurrentAdmin)]):
    redirect_path = request.url_for("login").__str__()

    key = Fernet.generate_key()
    print(key)
    fernetEncoder = Fernet(key=key)

    username = fernetEncoder.encrypt(USERNAME_MQTT.encode())
    password = fernetEncoder.encrypt(PASSWORD_MQTT.encode())

    if current_admin is None:
        return RedirectResponse(
            redirect_path + '?state=x-error-n-0',
            status_code=status.HTTP_302_FOUND
        )

    status_, content = current_admin

    if not status_:
        return RedirectResponse(
            redirect_path + f'?state=x-error-n-1&error={content.get("status")}',
            status_code=status.HTTP_302_FOUND
        )

    current_admin = content

    electrical_department_projects = await db.get_collection(Collections.PROJECT).find(
        {Project.DEPARTMENT_ID: 1, Project.IS_WORKING_ON: True, Project.IS_ACTIVE: True}).to_list(None)
    it_department_projects = await db.get_collection(Collections.PROJECT).find(
        {Project.DEPARTMENT_ID: 2, Project.IS_WORKING_ON: True,  Project.IS_ACTIVE: True}).to_list(None)
    managment_department_projects = await db.get_collection(Collections.PROJECT).find(
        {Project.DEPARTMENT_ID: 3, Project.IS_WORKING_ON: True,  Project.IS_ACTIVE: True}).to_list(None)

    electrical_department_projects = list(
        map(lambda item: from_bson(item, model.Project.Project).model_dump(), electrical_department_projects)
    )
    it_department_projects = list(
        map(lambda item: from_bson(item, model.Project.Project).model_dump(), it_department_projects)
    )

    managment_department_projects = list(
        map(lambda item: from_bson(item, model.Project.Project).model_dump(), managment_department_projects)
    )

    electrical_department_projects = list(map(lambda item: transfom_date(item), electrical_department_projects))
    it_department_projects = list(map(lambda item: transfom_date(item), it_department_projects))
    managment_department_projects = list(map(lambda item: transfom_date(item), managment_department_projects))

    electrical_department_projects = json.dumps(electrical_department_projects)
    it_department_projects = json.dumps(it_department_projects)
    managment_department_projects = json.dumps(managment_department_projects)

    list_of_bson_object_ele_department = await db.get_collection(Collections.HISTORY_DEPARTMENT).aggregate([
        {'$match': {HistoryDepartmentS.DEPARTMENT_ID: 1}},
        {'$group': {'_id': {'$dateToString': {'format': "%Y-%m-%d", 'date': "$date_time"}}, 'count': {'$sum': 1}}},
        {'$sort': {'_id': 1}},

    ]).to_list(None)

    list_of_bson_object_it_department = await db.get_collection(Collections.HISTORY_DEPARTMENT).aggregate([
        {'$match': {HistoryDepartmentS.DEPARTMENT_ID: 2}},

        {'$group': {'_id': {'$dateToString': {'format': "%Y-%m-%d", 'date': "$date_time"}}, 'count': {'$sum': 1}}},
        {'$sort': {'_id': 1}},

    ]).to_list(None)

    list_of_bson_object_mgt_department = await db.get_collection(Collections.HISTORY_DEPARTMENT).aggregate([
        {'$match': {HistoryDepartmentS.DEPARTMENT_ID: 3}},
        {'$group': {'_id': {'$dateToString': {'format': "%Y-%m-%d", 'date': "$date_time"}}, 'count': {'$sum': 1}}},
        {'$sort': {'_id': 1}},
    ]).to_list(None)

    dict_without_bson_id_ele = list(
        map(lambda item: from_bson(item, CountDateHistory).model_dump_json(), list_of_bson_object_ele_department))
    dict_without_bson_id_it = list(
        map(lambda item: from_bson(item, CountDateHistory).model_dump_json(), list_of_bson_object_it_department))
    dict_without_bson_id_mgt = list(
        map(lambda item: from_bson(item, CountDateHistory).model_dump_json(), list_of_bson_object_mgt_department))

    print(username)

    response = templates.TemplateResponse(
        request=request, name='dashboard.htm',
        context={'admin': current_admin,
                 'ele_projects': electrical_department_projects,
                 'it_projects': it_department_projects,
                 'mgt_projects': managment_department_projects,
                 'ele_history': dict_without_bson_id_ele,
                 'it_history': dict_without_bson_id_it,
                 'mgt_history': dict_without_bson_id_mgt,
                 'mqtt_username': username.decode("utf-8"),
                 'mqtt_password': password.decode('utf-8'),
                 'key': key.decode('utf-8')
                 }
    )

    return response


# @admin_route.get('/all_data')
# async def get_data(request: Request, response_username=Depends(getCurrentAdmin)):

#     if response_username is not str:
#         return response_username

#     print(response_username)


@admin_route.get('/pa_history', name='pa_history')
async def get_secure_history(request: Request, current_admin: Annotated[tuple | None, Depends(getCurrentAdmin)]):
    """
        boilerplate code of authentication :)
    
    """

    redirect_path = request.url_for("login").__str__()


    if current_admin is None:
        return RedirectResponse(
            redirect_path + '?state=x-error-n-0',
            status_code=status.HTTP_302_FOUND
        )


    status_, content = current_admin

    if not status_:
        return RedirectResponse(
            redirect_path + f'?state=x-error-n-1&error={content.get("status")}',
            status_code=status.HTTP_302_FOUND
        )

    # end of pbc

    history_of_place_a = await db.get_collection(Collections.HISTORY_SECURE).find().sort({HistorySecureS.DATE_TIME: -1}).to_list(None)
    pydantic_list = list(map(lambda item: from_bson(item, HistorySecureResponse), history_of_place_a))

    return templates.TemplateResponse(request=request, name='history_secure.htm', context={
        'admin': content,
        'list_secure': pydantic_list
    })


@admin_route.get('/pa_history/details', name='history_details')
async def secure_history_details(manager_id: str, datetime_: str, request: Request,
                                 current_admin: Annotated[tuple | None, Depends(getCurrentAdmin)]):
    # boilerplate code of authentication :)

    redirect_path = request.url_for("login").__str__()

    redirect_path = request.url_for("login").__str__()

    if current_admin is None:
        return RedirectResponse(
            redirect_path + '?state=x-error-n-0',
            status_code=status.HTTP_302_FOUND
        )

    status_, content = current_admin

    if not status_:
        return RedirectResponse(
            redirect_path + f'?state=x-error-n-1&error={content.get("status")}',
            status_code=status.HTTP_302_FOUND
        )

    # end of pbc

    if not ObjectId.is_valid(manager_id):
        return "Small Technical Problem"

    manager = await db.get_collection(Collections.USER).find_one({User.ID_: ObjectId(manager_id)})

    current_template = templates.TemplateResponse(
        request,
        name='history_details_info.htm',
        context={
            'admin': content,
            'manager': manager,
            'datetime_': datetime_
        }

    )

    return current_template


@admin_route.get('/department/{department_id}', name='department')
async def department_(department_id: int, request: Request,
                      current_admin: Annotated[tuple | None, Depends(getCurrentAdmin)]):
    """
        boilerplate code of authentication :)
    
    """


    details_employer_url = f'${request.base_url}/employer/details/'
    details_project_url = f'${request.base_url}/employer/details/'

    redirect_path = request.url_for("login").__str__()


    if current_admin is None:
        return RedirectResponse(
            redirect_path + '?state=x-error-n-0',
            status_code=status.HTTP_302_FOUND
        )

    status_, content = current_admin

    if not status_:
        return RedirectResponse(
            redirect_path + f'?state=x-error-n-1&error={content.get("status")}',
            status_code=status.HTTP_302_FOUND
        )

    # end of pbc

    department_info = await db.get_collection(Collections.DEPARTMENT).find_one(
        {DepartmentS.DEPARTMENT_IDENTIFICATION: department_id})
    department_without_bson = from_bson(department_info, Department)

    employers_of_department = await db.get_collection(Collections.USER).find(
        {User.ID_DEPARTMENT: department_id, User.IS_ACTIVE: True}).sort(
        {User.ROLE: 1}
    ).to_list(None)

    list_employers_without_bson_id = list(
        map(lambda item: from_bson(item, Employer.EmployerResponse), employers_of_department))

    projects_of_department = await db.get_collection(Collections.PROJECT).find(
        {Project.DEPARTMENT_ID: department_id, Project.IS_ACTIVE: True}).to_list(None)
    projects_of_department_without_bson_id = list(
        map(lambda item: from_bson(item, model.Project.ProjectResponse), projects_of_department))

    history_of_department = await db.get_collection(Collections.HISTORY_DEPARTMENT).find(
        {HistoryDepartmentS.DEPARTMENT_ID: department_id}).sort({HistoryDepartmentS.DATE_TIME: -1}).to_list(None)
    history_of_department_without_bson_id = list(
        map(lambda item: from_bson(item, model.History.HistoryDepartment), history_of_department))

    print(list_employers_without_bson_id)
    print(list_employers_without_bson_id[0].full_name)
    response = templates.TemplateResponse(
        request,
        'department.htm',
        context={
            'admin': content,
            'department': department_without_bson,
            'employers': list_employers_without_bson_id,
            'historys': history_of_department_without_bson_id,
            'projects': projects_of_department_without_bson_id,
            'id_dep': department_id,
            'project_details_url': details_project_url,
            'employer_details_url': details_employer_url

        }
    )

    return response


@admin_route.get('/add_employer/{dep_identifier}', name='view_add_employer')
async def add_employer(request: Request, dep_identifier: int,
                       current_admin: Annotated[tuple | None, Depends(getCurrentAdmin)]):
    """
        boilerplate code of authentication :)
    
    """

    redirect_path = request.url_for("login").__str__()


    if current_admin is None:
        return RedirectResponse(
            redirect_path + '?state=x-error-n-0',
            status_code=status.HTTP_302_FOUND
        )

    status_, content = current_admin

    if not status_:
        return RedirectResponse(
            redirect_path + f'?state=x-error-n-1&error={content.get("status")}',
            status_code=status.HTTP_302_FOUND
        )

    # end of pbc

    department: dict = await db.get_collection(Collections.DEPARTMENT).find_one(
        {DepartmentS.DEPARTMENT_IDENTIFICATION: dep_identifier})

    if department is None:
        return

    response = templates.TemplateResponse(
        request,
        name='addemployer.htm',
        context={
            'admin': content,
            'dep_identifier_': dep_identifier,
            'name_dep': department.get(DepartmentS.DEPARTMENT_NAME)
        }
    )

    return response


@admin_route.post('/store/employer', name='store_employer')
async def store_employer(request: Request,
                         username: Annotated[str, Form()],
                         password: Annotated[str, Form()],
                         email: Annotated[str, Form()],
                         id_dep: Annotated[int, Form()],
                         current_admin: Annotated[tuple | None, Depends(getCurrentAdmin)],

                         ):
    #        boilerplate code of authentication :)

    redirect_path = request.url_for("login").__str__()


    if current_admin is None:
        return RedirectResponse(
            redirect_path + '?state=x-error-n-0',
            status_code=status.HTTP_302_FOUND
        )

    status_, content = current_admin

    if not status_:
        return RedirectResponse(
            redirect_path + f'?state=x-error-n-1&error={content.get("status")}',
            status_code=status.HTTP_302_FOUND
        )

    # end of pbc

    if not check_username(username):
        return RedirectResponse(
            request.url_for(
                'view_add_employer', dep_identifier=id_dep
            ).include_query_params(username='false'),
            status_code=status.HTTP_302_FOUND
        )

    if len(password) < 8:
        return RedirectResponse(
            request.url_for(
                'view_add_employer', dep_identifier=id_dep
            ).include_query_params(password='false'),
            status_code=status.HTTP_302_FOUND
        )

    password = crypt_pass(password)

    employerRequest = Employer.EmployerRequest(
        nid='',
        full_name=username,
        email=email,
        password=password,
        id_dep=id_dep,
    ).model_dump()

    employerRequest.update({
        'create_at': datetime.datetime.now(tz=pytz.timezone('Africa/Tunis')),
        'update_at': datetime.datetime.now(tz=pytz.timezone('Africa/Tunis'))
    })

    try:
        user_id = await db.get_collection(Collections.USER).insert_one(employerRequest)
    except pymongo.errors.DuplicateKeyError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='email already exists')

    redirect = RedirectResponse(
        request.url_for('department', department_id=id_dep).include_query_params(status='success', content='a-employer',
                                                                                 section='x-turn-p'),
        status_code=status.HTTP_302_FOUND)

    return redirect


@admin_route.get('/employer/details/{id_}', name='employer_details')
async def get_employer_details(id_: str, request: Request,
                               current_admin: Annotated[tuple | None, Depends(getCurrentAdmin)]):
    #        boilerplate code of authentication :)

    redirect_path = request.url_for("login").__str__()


    if current_admin is None:
        return RedirectResponse(
            redirect_path + '?state=x-error-n-0',
            status_code=status.HTTP_302_FOUND
        )

    status_, content = current_admin

    if not status_:
        return RedirectResponse(
            redirect_path + f'?state=x-error-n-1&error={content.get("status")}',
            status_code=status.HTTP_302_FOUND
        )

    # end of pbc

    if not ObjectId.is_valid(id_):
        return RedirectResponse(
            request.url_for('login').include_query_params(error='D4'),
            status_code=status.HTTP_302_FOUND
        )

    employer: dict = await db.get_collection(Collections.USER).find_one({'_id': ObjectId(id_)})
    

    if employer is None:
        return RedirectResponse(
            request.url_for('login').include_query_params(error='D3'),
            status_code=status.HTTP_302_FOUND
        )

    department_ = await db.get_collection(Collections.DEPARTMENT).find_one(
        {DepartmentS.DEPARTMENT_IDENTIFICATION: employer.get(User.ID_DEPARTMENT)})
    department_ = from_bson(department_, Department)

    history_of_user = await db.get_collection(Collections.HISTORY_DEPARTMENT).find({HistoryDepartmentS.EMPLOYER_ID: str(employer.get(User.ID_)) }).to_list(None)

    history_of_user = list(map(lambda item: from_bson(item, model.History.HistoryDepartment),history_of_user))

    response = templates.TemplateResponse(
        request,
        'employer_details.htm',

        context={
            'employer': employer,
            'id_': id_,
            'admin': current_admin,
            'department': department_,
            'history' : history_of_user
        }

    )

    return response


@admin_route.post('/update_manager', name='update_manager')
async def update_manager(request: Request, face_coding: Annotated[str, Form()], department: Annotated[int, Form()],
                         employer: Annotated[str, Form()],
                         current_admin: Annotated[tuple | None, Depends(getCurrentAdmin)]):
    #        boilerplate code of authentication :)

    redirect_path = request.url_for("login").__str__()

    if current_admin is None:
        return RedirectResponse(
            redirect_path + '?state=x-error-n-0',
            status_code=status.HTTP_302_FOUND
        )

    status_, content = current_admin

    if not status_:
        return RedirectResponse(
            redirect_path + f'?state=x-error-n-1&error={content.get("status")}',
            status_code=status.HTTP_302_FOUND
        )

    # end of pbc

    face_coding_ = list(map(lambda item: float(item), face_coding.split(',')))

    redirectError = RedirectResponse(
        request.url_for('employer_details', id_=employer).include_query_params(error_update='true'),
        status_code=status.HTTP_302_FOUND)

    if len(face_coding_) != 128:
        return redirectError

    res_ = await db.get_collection(Collections.USER).update_one(
        {User.ID_: ObjectId(employer)},
        {'$set': {User.FACE_CODDING: face_coding_, User.ROLE: Roles.D_MANAGER}}
    )

    if not res_.modified_count == 1:
        return "None"

    res_of_update = await db.get_collection(Collections.USER).update_many(
        {User.ROLE: Roles.D_MANAGER, User.ID_DEPARTMENT: department, User.ID_: {'$ne': ObjectId(employer)}},
        {'$set': {User.ROLE: Roles.EMPLOYER}}
    )

    if res_of_update.modified_count == 0:
        return "None of You"

    if res_.modified_count == 0:
        return redirectError

    return RedirectResponse(
        request.url_for('employer_details', id_=employer).include_query_params(success_update='true'),
        status_code=status.HTTP_302_FOUND)


# project routes

## add project
@admin_route.get('/project/add_view/{dep_id}', name='add_project_view')
async def add_project_view(request: Request, dep_id: int,
                           current_admin: Annotated[tuple | None, Depends(getCurrentAdmin)]):
    #        boilerplate code of authentication :)

    redirect_path = request.url_for("login").__str__()

    if current_admin is None:
        return RedirectResponse(
            redirect_path + '?state=x-error-n-0',
            status_code=status.HTTP_302_FOUND
        )

    status_, content = current_admin

    if not status_:
        return RedirectResponse(
            redirect_path + f'?state=x-error-n-1&error={content.get("status")}',
            status_code=status.HTTP_302_FOUND
        )

    # end of pbc

    current_department = await db.get_collection(Collections.DEPARTMENT).find_one(
        {DepartmentS.DEPARTMENT_IDENTIFICATION: dep_id})

    current_department = from_bson(current_department, Department)

    if current_admin is None:
        return "Same Thing Went Wrong"

    response = templates.TemplateResponse(
        request=request,
        name='addproject.htm',
        context={
            'admin': content,
            'department': current_department,
        }
    )

    return response


## update project section


@admin_route.get('/project/update_view/{dep_id}/{project_id}', name='update_project_view')
async def add_project_view(request: Request, dep_id: int, project_id: str,
                           current_admin: Annotated[tuple | None, Depends(getCurrentAdmin)]):
    #        boilerplate code of authentication :)

    redirect_path = request.url_for("login").__str__()

    if current_admin is None:
        return RedirectResponse(
            redirect_path + '?state=x-error-n-0',
            status_code=status.HTTP_302_FOUND
        )

    status_, content = current_admin

    if not status_:
        return RedirectResponse(
            redirect_path + f'?state=x-error-n-1&error={content.get("status")}',
            status_code=status.HTTP_302_FOUND
        )

    # end of pbc

    if not ObjectId.is_valid(project_id):
        return RedirectResponse(
            redirect_path + f'?state=x-error-n-5&error=id-not-valid',
            status_code=status.HTTP_302_FOUND
        )

    current_department = await db.get_collection(Collections.DEPARTMENT).find_one(
        {DepartmentS.DEPARTMENT_IDENTIFICATION: dep_id})
    current_project = await db.get_collection(Collections.PROJECT).find_one({Project.ID_: ObjectId(project_id)})

    if current_admin is None or current_project is None or current_department is None:
        return "Same Thing Went Wrong"

    current_department = from_bson(current_department, Department)
    current_project = from_bson(current_project, model.Project.ProjectResponse)

    print(current_project)

    response = templates.TemplateResponse(
        request=request,
        name='updateproject.htm',
        context={
            'admin': content,
            'department': current_department,
            'project': current_project
        }
    )

    return response


@admin_route.post('/project/update_store/{id_dep_}', name='update_project_store')
async def update_store_project(
        request: Request,
        current_admin: Annotated[tuple | None, Depends(getCurrentAdmin)],
        id_dep_: int,
        # form data
        project_id: Annotated[str, Form()],
        project_label: Annotated[str, Form()],
        project_client_brand: Annotated[str, Form()],
        project_client_location: Annotated[str, Form()],
        project_description: Annotated[str, Form()],
        project_start_at: Annotated[datetime.datetime, Form()],
        project_end_at: Annotated[datetime.datetime, Form()],
        project_delay: Annotated[int, Form()],
        started: Annotated[str | None, Form()] = None
):
    error_redirect_object = request.url_for('add_project_view', dep_id=id_dep_)

    if not ObjectId.is_valid(project_id):
        return RedirectResponse(
            request.url_for('login').include_query_params(state='error-n0', error='x-error-body'),
            status_code=status.HTTP_302_FOUND
        )

    current_department = db.get_collection(Collections.DEPARTMENT).find_one(
        {DepartmentS.DEPARTMENT_IDENTIFICATION: id_dep_})

    if current_department is None:
        return RedirectResponse(
            request.url_for('login').include_query_params(state='error-n0', error='x-error-url'),
            status_code=status.HTTP_302_FOUND
        )

    if not string_validate(project_label):
        return RedirectResponse(
            error_redirect_object.include_query_params(status='error-n2', error='x-error-label-invalid'),
            status_code=status.HTTP_302_FOUND)

    if not string_validate(project_client_brand, max=128):
        return RedirectResponse(
            error_redirect_object.include_query_params(status='error-n2', error='x-error-client_brand-invalid'),
            status_code=status.HTTP_302_FOUND
        )

    if not string_validate(project_client_location, max=256, include_sepc_char=True):
        return RedirectResponse(
            error_redirect_object.include_query_params(status='error-n2', error='x-error-client_location-invalid'),
            status_code=status.HTTP_302_FOUND)

    if project_start_at > project_end_at:
        return RedirectResponse(
            error_redirect_object.include_query_params(status='error-n2', error='x-error-date-invalid'),
            status_code=status.HTTP_302_FOUND)

    project_model = model.Project.ProjectUpdate(
        _id=project_id,
        label=project_label,
        description=project_description,
        client_brand=project_client_brand,
        client_location=project_client_location,
        is_working_on=started is not None,
        start_at=project_start_at,
        end_at=project_end_at,
        functional_delay=str(project_delay),
    )

    project_add = await db.get_collection(Collections.PROJECT).update_one({Project.ID_: ObjectId(project_id)},
                                                                          {'$set': project_model.model_dump()})

    fast_mqtt.publish(f"/project/update/{id_dep_}", project_id)

    return RedirectResponse(
        url=request.url_for('department', department_id=id_dep_).include_query_params(status='success',
                                                                                      content='u-project'),
        status_code=status.HTTP_302_FOUND
    )


@admin_route.post('/project/add_store/{id_dep_}', name='add_project_store')
async def add_project_admin(
        request: Request,
        current_admin: Annotated[tuple | None, Depends(getCurrentAdmin)],
        id_dep_: int,
        # form data
        project_label: Annotated[str, Form()],
        project_client_brand: Annotated[str, Form()],
        project_client_location: Annotated[str, Form()],
        project_description: Annotated[str, Form()],
        project_start_at: Annotated[datetime.datetime, Form()],
        project_end_at: Annotated[datetime.datetime, Form()],
        project_delay: Annotated[int, Form()],
        started: Annotated[str | None, Form()] = None
):
    error_redirect_object = request.url_for('add_project_view', dep_id=id_dep_)

    current_department = db.get_collection(Collections.DEPARTMENT).find_one(
        {DepartmentS.DEPARTMENT_IDENTIFICATION: id_dep_})

    if current_department is None:
        return RedirectResponse(
            request.url_for('login').include_query_params(state='error-n0', error='x-error-url'),
            status_code=status.HTTP_302_FOUND
        )

    if not string_validate(project_label):
        return RedirectResponse(
            error_redirect_object.include_query_params(status='error-n2', error='x-error-label-invalid'),
            status_code=status.HTTP_302_FOUND)

    if not string_validate(project_client_brand, max=128):
        return RedirectResponse(
            error_redirect_object.include_query_params(status='error-n2', error='x-error-client_brand-invalid'),
            status_code=status.HTTP_302_FOUND
        )

    if not string_validate(project_client_location, max=256, include_sepc_char=True):
        return RedirectResponse(
            error_redirect_object.include_query_params(status='error-n2', error='x-error-client_location-invalid'),
            status_code=status.HTTP_302_FOUND)

    if project_start_at > project_end_at:
        return RedirectResponse(
            error_redirect_object.include_query_params(status='error-n2', error='x-error-date-invalid'),
            status_code=status.HTTP_302_FOUND)

    create_at = datetime.datetime.now()
    update_at = datetime.datetime.now()

    project_model = model.Project.Project(
        label=project_label,
        description=project_description,
        client_brand=project_client_brand,
        client_location=project_client_location,
        is_working_on=started is not None,
        create_at=create_at,
        update_at=update_at,
        start_at=project_start_at,
        end_at=project_end_at,
        functional_delay=str(project_delay),
        department_identification=id_dep_
    )

    project_add = await db.get_collection(Collections.PROJECT).insert_one(project_model.model_dump())
    fast_mqtt.publish(f"/project/add/{id_dep_}", str(project_add.inserted_id))

    return RedirectResponse(
        url=request.url_for('department', department_id=id_dep_).include_query_params(status='success',
                                                                                      content='a-project'),
        status_code=status.HTTP_302_FOUND
    )


@admin_route.get('/logout', name='logout')
def logout_(request: Request, current_admin: Annotated[tuple | None, Depends(getCurrentAdmin)]):
    return_back = RedirectResponse(
        request.url_for('login'),
        status_code=status.HTTP_302_FOUND,
    )

    return_back.delete_cookie('session_id')
    return return_back


# search part ( all search methods by labels ) # no need to authenticated for this process

@admin_route.get("/search", name='search')
async def search_project_by_label(request: Request,q: str, collection_name: Collections,dep_identifier: int, current_admin=Depends(getCurrentAdmin)):
    # no validation of current authenticated

    if collection_name not in [Collections.PROJECT, Collections.USER]:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE, detail="problem with your query"
        )




    keywords = q.split(" ")

    keywords = list(filter(lambda keyword_: keyword_.isalnum(), keywords))
    final_keyword = " ".join(keywords).strip()
    regx = bson.regex.Regex(final_keyword)

    field_to_search, model__, department_identifier = (
        Project.LABEL, model.Project.ProjectResponse, Project.DEPARTMENT_ID) if collection_name == Collections.PROJECT else (
        User.FULL_NAME, model.Employer.EmployerResponse, User.ID_DEPARTMENT)

    res = await db.get_collection(collection_name).find({field_to_search: regx, department_identifier: dep_identifier, 'is_active': True }).to_list(6)
    res = list(map(lambda item: from_bson(item, model__), res))

    return res




@admin_route.get('/project/{id_project}')
async def get_project_by_id(id_project: str, current_user: dict = Depends(getCurrentAdmin)):
    is_bson_id(id_project)
    bson_id = ObjectId(id_project)

    if not current_user[0]:
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='session complate')
    
    project_as_bison = await db.get_collection(Collections.PROJECT).find_one({'_id': bson_id})

    if project_as_bison is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Projects With ID {id_project}"
        )

    return from_bson(project_as_bison, model.Project.ProjectResponse)


@admin_route.post("/employer/{id_dep}/deactive/{employer_id}", name='delete-employer')
async def deactiveEmployer(id_dep: int,employer_id: str, request: Request, current_admin = Depends(getCurrentAdmin)):
    is_active, admin = current_admin

    
    if not is_active:
        return RedirectResponse(request.url_for('login').include_query_params(status = admin.get('status')))

    employer_suspended = await db.get_collection(Collections.USER).update_one({User.ID_: ObjectId(employer_id), User.ROLE: {'$ne': Roles.ADMIN}, User.ROLE: {'$ne': Roles.D_MANAGER}}, { '$set' : {User.IS_ACTIVE: False}})
    
    redirectPath = request.url_for('department', department_id = id_dep)


    if employer_suspended.modified_count > 0:
        redirectPath = redirectPath.include_query_params(status = 'success',content='employer-deactivated',  section = 'x-turn-e')
    else:
        redirectPath = redirectPath.include_query_params(status = 'error', content='employer-deactivate', section = 'x-turn-e')


    return RedirectResponse(
                redirectPath, status_code=status.HTTP_302_FOUND
        )
    




@admin_route.get('/project/delete/{dep_id}/{project_id}', name='delete-project')
async def delete_project(request: Request, dep_id: int, project_id: str, current_admin = Depends(getCurrentAdmin)):

    is_active, admin = current_admin
    

    if not is_active:
        return RedirectResponse(request.url_for('login').include_query_params(status = admin.get('status')))

    
    if not ObjectId.is_valid(project_id):
        return RedirectResponse(request.url_for('login').include_query_params(status = 'invalid url'))

    
    delete_sessions_of_project = await db.get_collection(Collections.PROJECT).update_one({ Project.ID_: ObjectId(project_id) }, { '$set' : {Project.IS_ACTIVE: False}})

     
    redirectPath = request.url_for('department', department_id = dep_id)


    if delete_sessions_of_project.modified_count > 0:
        redirectPath = redirectPath.include_query_params(status = 'success',content='project-deleted',  section = 'x-turn-p')
    else:
        redirectPath = redirectPath.include_query_params(status = 'error', content='project-deleted', section = 'x-turn-p')


    
    
    return RedirectResponse(
                redirectPath, status_code=status.HTTP_302_FOUND
        )
