import bson
from bson.objectid import ObjectId
from hashlib import sha256
from fastapi import HTTPException
from starlette import status

IS_PROTECTION = False


def from_bson(bsion: dict, Model):
    dict_ = {k: v for k, v in bsion.items() if type(v) != ObjectId}
    id_ = bsion['_id']
    id_ = str(id_)
    dict_.update({'_id': id_})
    return Model(**dict_)


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
