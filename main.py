import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException

from route.routes_employer import employer_route
from route.login_route import login_route
from starlette import status

from database_config.configdb import Database
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    Database()
    yield
    print('Bay')


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.get('/')
async def main_route():
    db = Database()
    list_of_users = await db.list_collection_names()
    return list_of_users

app.include_router(router=employer_route, tags=['Employer Actions'])
app.include_router(router=login_route, tags=['Login'])


if __name__ == '__main__':
    uvicorn.run('main:app', reload=True)
