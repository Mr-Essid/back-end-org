from fastapi import APIRouter
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

admin_route = APIRouter(prefix='/admin')

templates = Jinja2Templates("templates")
admin_route.get('/login')


def loginGet(request: Request):
    return templates.TemplateResponse("index.html", {'request': request})
