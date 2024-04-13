from datetime import datetime, timedelta
from jose import jwt
from pydantic import BaseModel

from env import load_env_jwt

SECRET_KEY = load_env_jwt()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=1)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decodeAccessToken(token: str):
    data_ = jwt.decode(token, algorithms=ALGORITHM, key=SECRET_KEY)
    return data_


class Token(BaseModel):
    access_token: str
    token_type: str
