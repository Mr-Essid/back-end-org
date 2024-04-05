from bson.objectid import ObjectId
from hashlib import sha256

IS_PROTECTION = False

def from_bson(bsion: dict, Model):
    dict_ = {k: v for k, v in bsion.items() if type(v) != ObjectId}
    id_ = bsion['_id']
    id_ = str(id_)
    dict_.update({'_id': id_})
    return Model(**dict_)


def crypt_pass(password: str) -> str:
    _ = sha256()
    _.update(password.encode())
    return _.hexdigest()


def verify_password(password_, hashed_password):
    _ = sha256()
    _.update(password_.encode())
    hashed_ = _.hexdigest()
    return hashed_ == hashed_password
