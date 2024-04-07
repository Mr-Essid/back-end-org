import datetime
import os
import random
import string

from pymongo.errors import DuplicateKeyError
from fastapi import APIRouter, HTTPException, Depends
from starlette import status
from starlette.requests import Request

import schemes
from database_config.configdb import db
from model.Employer import EmployerRequest, EmployerResponse, EmployerUpdate, UpdatePassword, EmployerUpdatePrivate, \
    Roles, UpgradeEmployer
from bson.objectid import ObjectId
from database_config.Collections import Collections
from schemes import User
from utiles import from_bson, verify_password, crypt_pass, is_bson_id, RaspberryPi_Admin, Admin_Department_manager, \
    Employer_access, Admin_only
from fastapi_mail import ConnectionConfig, MessageSchema, MessageType, FastMail
from env import load_smtp
from .login_route import get_current_user
from .project_route import check_for_contributed_resources, check_permission

employer_route = APIRouter(prefix='/employers')
host_smtp, username_smtp, password_smtp, from_mail, from_name, port = load_smtp()

access_forbidden = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Request Not Permitted")

conf = ConnectionConfig(
    MAIL_USERNAME=username_smtp,
    MAIL_PASSWORD=password_smtp,
    MAIL_FROM=from_mail,
    MAIL_PORT=port,
    MAIL_SERVER=host_smtp,
    MAIL_FROM_NAME=from_name,
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    TEMPLATE_FOLDER='./email_models'
)



@employer_route.get('/v/email-verify')
async def active_account(key: str, request: Request):
    is_bson_id(key)
    user = await db.get_collection(Collections.USER).find_one({'_id': ObjectId(key)})
    state = user['email_verified']
    if state:
        return {'status': 'Account Verified', 'details': 'check your email we have sent to your credentials'}

    if user is None:
        return {
            'status': 'Validation Expired'
        }

    host = request.url.scheme + "://"
    host += request.headers['host']
    message = MessageSchema(
        subject="Activation",
        recipients=['iotek.host@gmail.com'],
        subtype=MessageType.html,
        template_body={'user': user}
    )

    fm = FastMail(conf)
    await fm.send_message(message, template_name='validated.html')
    res = await db.get_collection(Collections.USER).update_one({'_id': ObjectId(key)},
                                                               {'$set': {'email_verified': True}})

    return {
        'status': 'Your Account Activated Successfully'
    } if res.modified_count >= 1 else {
        'status': 'Same Thing Went Wrong Your Account Already Activated'
    }


@employer_route.get('/v/forget_password/{email}')
async def forget_password(email: str):
    user_ = await db.get_collection(Collections.USER).find_one({'email': email})

    if user_ is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="your email are not correct")

    if not user_[User.ROLE] == Roles.EMPLOYER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='please call your administrator'
        )

    new_pass_gen = ''.join(random.choices(string.digits + string.hexdigits + string.ascii_letters, k=20))

    current_date = datetime.datetime.today()
    last_update = user_[User.UPDATE_AT]
    delay_of_change = (current_date - last_update).days

    if delay_of_change < 15:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f'Your Have to Wait {15 - delay_of_change} day to Change Password'
        )

    message = MessageSchema(
        subject="Forget Password",
        recipients=['iotek.host@gmail.com'],
        subtype=MessageType.html,
        template_body={'user': user_, 'new_password': new_pass_gen}
    )

    fm = FastMail(conf)
    await fm.send_message(message, template_name='forget_password.html')

    hashed_new_password = crypt_pass(new_pass_gen)
    res = await db.get_collection(Collections.USER).update_one({'email': email}, {
        '$set': {'password': hashed_new_password, 'update_at': datetime.datetime.today()}})

    return {
        'status': 'password modified, check your email'
    }


@employer_route.get('/department/managers', tags=RaspberryPi_Admin)
async def employers_get_department_managers(current_user=Depends(get_current_user)):
    """
    :key:\n
        Access only by RaspberryPI
    :return:
    will be like\n
    [{\n
    department:\n
        Department\n
    manager:\n
        EmployerResponse\n
    }, ...]
    """
    all_departments = await db.get_collection(Collections.DEPARTMENT).find({}, {'_id': 0}).to_list(15)

    # we can't use async with map :(
    async def get_manager_and_department(department_dict: dict):
        department_id = department_dict[schemes.DepartmentS.DEPARTMENT_IDENTIFICATION]
        manager_of_department = await db.get_collection(Collections.USER).find_one(
            {User.ROLE: Roles.D_MANAGER, User.ID_DEPARTMENT: department_id})

        if manager_of_department is not None:
            manager_of_department = from_bson(manager_of_department, EmployerResponse)

        return {
            'department': department_dict,
            'manager': manager_of_department
        }

    all_departments_with_there_managers = [await get_manager_and_department(department) for department in
                                           all_departments]
    return all_departments_with_there_managers


@employer_route.get('/department/{id_depart}', tags=Admin_Department_manager)
async def employers_of_department(id_department: int, page: int = 1, current_user: dict = Depends(get_current_user)):
    page = (page - 1) * 15
    check_for_contributed_resources(current_user, id_department)
    check_permission(current_user, [Roles.D_MANAGER, Roles.ADMIN])
    list_employers_ = await db.get_collection(Collections.USER).find({schemes.User.ID_DEPARTMENT: id_department}).skip(
        page).limit(15).to_list(15)
    if len(list_employers_) == 0:
        return []
    list_python_ = list(map(lambda item: from_bson(item, EmployerResponse), list_employers_))
    return list_python_


@employer_route.get('/{id_user}', tags=Employer_access)
async def employer_by_id(id_user: str, current_user=Depends(get_current_user)):
    is_bson_id(id_user)

    if not (current_user[User.ROLE] == Roles.ADMIN or str(current_user[User.ID_]) == id_user):
        raise access_forbidden

    employer = await db.get_collection(Collections.USER).find_one({'_id': ObjectId(id_user), 'is_active': True})
    if employer is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="employer not found")

    return from_bson(employer, EmployerResponse)


@employer_route.get('/', tags=Admin_only)
async def get_employers(page: int = 1, current_user=Depends(get_current_user)):
    if current_user[User.ROLE] != Roles.ADMIN:
        raise access_forbidden

    if page < 1:
        page = 1
    skip = (page - 1) * 15
    list_employers = await db.get_collection(Collections.USER).find({'is_active': True}).skip(skip).limit(15).to_list(
        15)

    # fix small issue with deployment process
    if len(list_employers) == 0:
        return []
    list_employers = list(map(lambda item: from_bson(item, EmployerResponse), list_employers))
    return list_employers


@employer_route.post('/', tags=Admin_only)
async def add_employer(user: EmployerRequest, request: Request, current_user=Depends(get_current_user)):
    if current_user[User.ROLE] != Roles.ADMIN:
        raise access_forbidden

    user = user.model_dump(by_alias=True)
    user.update({'create_at': datetime.datetime.today()})
    user.update({'update_at': datetime.datetime.today()})
    user[User.PASSWORD] = crypt_pass(user[User.PASSWORD])
    try:
        user_id = await db.get_collection(Collections.USER).insert_one(user)
    except DuplicateKeyError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='email already exists')

    user_ = await db.get_collection(Collections.USER).find_one({'_id': ObjectId(user_id.inserted_id)})

    # send mail validation
    id_ = user_['_id']
    state = user_['email_verified']
    email = user_['email']
    username = user_['full_name']
    host = request.url.scheme + "://"
    host += request.headers['host']
    current_validation = os.path.join(host, 'employers', 'v', f'email-verify?key={id_}')
    message = MessageSchema(
        subject="Validation",
        recipients=['iotek.host@gmail.com'],
        subtype=MessageType.html,
        template_body={'user': user_, 'url': current_validation}
    )

    fm = FastMail(conf)
    await fm.send_message(message, template_name='validation.html')
    return from_bson(user_, EmployerResponse)


@employer_route.put('/', tags=Employer_access)
async def update(data: EmployerUpdate, current_user=Depends(get_current_user)):
    is_bson_id(current_user[User.ID_])
    id_ = ObjectId(current_user[User.ID_])
    data_present = {k: v for k, v in data.__dict__.items() if v is not None}
    res = await db.get_collection(Collections.USER).update_one({'_id': id_}, {"$set": data_present})
    user = await db.get_collection(Collections.USER).find_one({'_id': id_})
    return {'employer': from_bson(user, EmployerResponse), 'is_modified': res.modified_count > 0}


@employer_route.put('/private', tags=Admin_only)
async def update_private(data: EmployerUpdatePrivate, current_user=Depends(get_current_user)):
    if current_user[User.ROLE] != Roles.ADMIN:
        raise access_forbidden

    is_bson_id(data.id_)
    id_ = ObjectId(data.id_)
    data_present = {k: v for k, v in data.__dict__.items() if v is not None}
    res = await db.get_collection(Collections.USER).update_one({'_id': id_}, {"$set": data_present})
    user = await db.get_collection(Collections.USER).find_one({'_id': id_})

    return {'employer': from_bson(user, EmployerResponse), 'is_modified': res.modified_count > 0}


@employer_route.put('/grade', tags=Admin_only)
async def upgrade_(data: UpgradeEmployer):
    data = data.model_dump()
    department = data['department_id']
    employer_ = data['employer_id']
    face_coding_of_employer = data['face_coding']

    if len(face_coding_of_employer) != 128:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='face coding is not compatible with the model')

    res_of_update = await db.get_collection(Collections.USER).update_one(
        {User.ROLE: Roles.D_MANAGER, User.ID_DEPARTMENT: department}, {'$set': {User.ROLE: Roles.EMPLOYER}})
    res_ = await db.get_collection(Collections.USER).update_one(
        {User.ID_: ObjectId(employer_)},
        {'$set': {User.FACE_CODDING: face_coding_of_employer}, User.ROLE: Roles.D_MANAGER}
    )

    if res_.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_304_NOT_MODIFIED,
            detail='No Modification Found'
        )

    return {
        'status': 'employer updated successfully'
    }


@employer_route.delete('/{id_}', tags=Admin_only)
async def soft_delete(id_: str, current_user=Depends(get_current_user)):
    if current_user[User.ROLE] != Roles.ADMIN:
        raise access_forbidden
    is_bson_id(id_)
    id_ = ObjectId(id_)
    res = await db.get_collection(Collections.USER).update_one({'_id': id_}, {'$set': {'is_active': False}})
    return {'state': 'Account Deleted Successfully'}


@employer_route.put('/password', tags=Employer_access)
async def update_pass(password: UpdatePassword, current_user: dict = Depends(get_current_user)):
    new_pass = password.new_password
    old_pass = password.old_password

    if not verify_password(old_pass, current_user[User.PASSWORD]):
        raise access_forbidden
    res = await db.get_collection(Collections.USER).update_one({'_id': ObjectId(current_user[User.ID_])}, {'$set': {
        User.PASSWORD: crypt_pass(new_pass)
    }})

    status_ = {}
    if res.modified_count > 0:
        status_.update({'status': 'password updated successfully'})

    if res.modified_count == 0 and res.matched_count == 1:
        status_.update({'statues': "your new password and old password are the same"})

    if res.matched_count == 0:
        status_.update({'statues': 'same things went wrong'})

    return status_
