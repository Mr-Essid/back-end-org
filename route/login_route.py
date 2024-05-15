from datetime import timedelta
from typing import Annotated

from fastapi import Depends, HTTPException
from starlette import status

from database_config.Collections import Collections
from database_config.configdb import db
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from fastapi import APIRouter
from env import load_env_jwt
from JWTUtilits import create_access_token, decodeAccessToken, Token, ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from schemes import User
from utiles import verify_password

KEY = load_env_jwt()

login_route = APIRouter(prefix='/api')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")


@login_route.post("/token")
async def login_for_access_token(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    user = await db.get_collection(Collections.USER).find_one({'email': form_data.username})



    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


    if not user.get(User.IS_ACTIVE):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Employer Not Activate",
            headers={"WWW-Authenticate": "Bearer"},
        )



    if not verify_password(form_data.password, user['password']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token({
        'sub': user['email']
    }, access_token_expires)

    return Token(access_token=access_token, token_type="bearer")


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await db.get_collection(Collections.USER).find_one({'email': username})
    user[User.ID_] = str(user[User.ID_])

    if user is None:
        raise credentials_exception

    return user
