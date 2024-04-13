from enum import StrEnum

from bson import ObjectId
from socketio import AsyncServer, ASGIApp, AsyncNamespace

import schemes
from JWTUtilits import decodeAccessToken
from database_config.Collections import Collections
from database_config.configdb import db


class DepartmentNameSpace(StrEnum):
    ELECTRICAL_DEPARTMENT = '/1'
    IT_DEPARTMENT = '/2'
    MGT_DEPARTMENT = '/3'


sio = AsyncServer(
    cors_allowed_origins="*",
    async_mode='asgi'
)

socket_io_app = ASGIApp(
    socketio_path='socket.io',
    socketio_server=sio
)


class Department(AsyncNamespace):
    async def on_connect(self, sid, environ: dict, auth: dict):
        username = 'anonymous'
        print(self.namespace)
        query_string: str = environ.get('QUERY_STRING')
        list_query = query_string.split('&')
        list_session_ids = list(filter(lambda str_: str_.__contains__('session_id'), list_query))

        session_id_key_value = list_session_ids[0].split('=')

        if len(session_id_key_value) != 2:
            return False

        session_id = session_id_key_value[1]
        session_: dict = await db.get_collection(Collections.SESSION).find_one(
            {schemes.Session.ID_: ObjectId(session_id)})
        if session_ is None or not session_.get(schemes.Session.ISALIVE):
            return False  # session expired

        if len(list_session_ids) == 0:
            return False
        if auth is not None:
            username = auth['username'] if auth['username'] is not None else 'anonymous'
            print(auth)
            bearer_token: str = auth.get('Authorization')

            array_of_token = bearer_token.split(" ")

            if len(array_of_token) != 2 or array_of_token[0] != 'Bearer':
                return False

            token = array_of_token[1]
            token_decode: dict = decodeAccessToken(token)
            username = auth.get('username')
            dep_id = auth.get('department_id')

            if username is None or dep_id is None:
                return False

            await self.save_session(sid, {
                'username': username,
                'dep_id': dep_id,
                'session_id': session_id
            })

            print(token_decode.get('sub'))

        print(session_)

        await self.save_session(sid, {'username': username})

    async def on_disconnect(self, sid):
        hisDict: dict = await self.get_session(sid)
        username = hisDict.get('username')
        await self.emit('e_disconnect', f'{username} disconnected')

    async def on_message(self, sid, data):
        data_user: dict = await self.get_session(sid)
        username = data_user.get('username')
        await self.emit('response', f'{username}: {data}', skip_sid=sid)
        return 'OK', 200

    async def on_discition(self, sid, data):
        data_user: dict = await self.get_session(sid)
        username = data_user.get('username')
        await self.emit('response', f'{username} : DESCITION {data}', skip_sid=sid)


sio.register_namespace(Department(DepartmentNameSpace.MGT_DEPARTMENT))
sio.register_namespace(Department(DepartmentNameSpace.IT_DEPARTMENT))
sio.register_namespace(Department(DepartmentNameSpace.ELECTRICAL_DEPARTMENT))
