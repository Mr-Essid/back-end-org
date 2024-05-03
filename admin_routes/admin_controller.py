from typing import Annotated

from fastapi import APIRouter, Depends, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from jose import ExpiredSignatureError, JWTError
from jose.exceptions import JWTClaimsError
from starlette.requests import Request
import datetime
from JWTUtilits import create_access_token, decodeAccessToken
from database_config.Collections import Collections
from database_config.configdb import db
from model.Employer import Roles
from utiles import verify_password

admin_route = APIRouter(prefix='/admin')

templates = Jinja2Templates("templates")


def getCurrentAdmin(request: Request, session_id: Annotated[str, Cookie()]):
    responseIfNotValid = templates.TemplateResponse(name='index.html', request=request)
    try:

        admin = decodeAccessToken(session_id).get('sub')
        return admin
    except (ExpiredSignatureError, JWTError, JWTClaimsError) as e:
        if type(e) is ExpiredSignatureError:
            responseIfNotValid.context.update({'session_expired': True})
        return responseIfNotValid


@admin_route.get('/login')
def loginGet(request: Request):
    return templates.TemplateResponse(name="index.html", request=request)


@admin_route.post('/dashboard', name='dashboard')
async def loginPost(request: Request, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    root: dict = await db.get_collection(Collections.USER).find_one({'email': form_data.username})

    if root is None:
        return templates.TemplateResponse(request=request, name='index.html', context={'login': 'error'},
                                          status_code=307)
    password = root.get('password')

    if not verify_password(form_data.password, password):
        return templates.TemplateResponse(request=request, name='index.html', context={'login': 'error'},
                                          status_code=307)

    if root.get('role') != Roles.ADMIN:
        return templates.TemplateResponse(request=request, name='index.html', context={'login': 'request not permitted'},
                                          status_code=307)

    response = templates.TemplateResponse(
        request=request, name='dashboard.html', context={'admin': root}
    )

    data = {'sub': root.get('email'), 'username': root.get('full_name'), 'role': root.get('role')}

    token = create_access_token(data, expires_delta=datetime.timedelta(hours=3))
    response.set_cookie("session_id", token)
    return response


@admin_route.get('/all_data')
async def get_data(request: Request, response_username=Depends(getCurrentAdmin)):

    if response_username is not str:
        return response_username

    print(response_username)

