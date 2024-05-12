import datetime
import string
import bson
from bson.objectid import ObjectId
from hashlib import sha256
from fastapi import HTTPException
from starlette import status

IS_PROTECTION = False

"""
    Actions Access
"""

Employer_access = ['Employer Actions']
Department_Manager_only = ['Department Manager Only Actions']
Admin_only = ['Admin Only Actions']
Admin_Department_manager = ['Admin - Department Manager Actions']
RaspberryPi_Admin = ['Admin - RaspberryPI Actions']


def from_bson(bsion: dict, Model):
    dict_ = {k: v for k, v in bsion.items() if type(v) != ObjectId}
    id_ = bsion['_id']
    id_ = str(id_)
    dict_.update({'_id': id_})
    return Model(**dict_)



def transfom_date(dict_with_datetime: dict):
    dict_ = {k: v for k, v in dict_with_datetime.items() if type(v) != datetime.datetime}
    dates = {k: str(v) for k, v in dict_with_datetime.items() if type(v) == datetime.datetime}
    
    dict_.update(dates)
    
    return dict_


def get_filled_only(instance_: dict):
    if type(instance_) is not dict:
        raise ValueError('Wrong input, you should have dict')
    filed_data = {k: v for k, v in instance_.items() if v is not None}
    return filed_data


def crypt_pass(password: str) -> str:
    _ = sha256()
    _.update(password.encode())
    return _.hexdigest()


def verify_password(password_, hashed_password):
    _ = sha256()
    _.update(password_.encode())
    hashed_ = _.hexdigest()
    return hashed_ == hashed_password


def is_bson_id(id_bson):
    if not ObjectId.is_valid(id_bson):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Id Not Valid'
        )



def check_username(username: str):

    for char_ in username:
        if char_ in string.punctuation:
            return False
        
    return len(username) >= 4 # at least 4 chars




# validation function utli

def string_validate(
        string_: str,
        max: int = 64,
        min: int = 4,
        include_sepc_char: bool = False,
        is_email: bool = False,
):
    if len(string_) > max or len(string_) < min:
        return False
    
    if not include_sepc_char:
        for char in string_:
            if char in string.punctuation:
                return False
    
    if is_email and not string_.__contains__('@'):
        return False
    
    return True 