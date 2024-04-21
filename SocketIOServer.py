import datetime
from enum import StrEnum

from bson import ObjectId
from jose import JWTError
from jose.exceptions import JWTClaimsError, ExpiredSignatureError
from socketio import AsyncServer, ASGIApp, AsyncNamespace
from socketio.exceptions import ConnectionRefusedError

import JWTUtilits
import schemes
from JWTUtilits import decodeAccessToken
from database_config.Collections import Collections
from database_config.configdb import db
from model.Message import Message, MessageType
from utiles import is_bson_id


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


async def save_message(message_content: str, type_: MessageType, employer_id: str, session_id: str):
    current_date = datetime.datetime.now()
    # message = Message(employer_id=employer_id, session_id=session_id, date_time=current_date, type_=type_,
    #                   message_content=message_content)

    message = {
        'employer_id': employer_id,
        'session_id': session_id,
        'date_time': current_date,
        'type_': type_,
        'message_content': message_content
    }

    res = await db.get_collection(Collections.MESSAGE).insert_one(message)


class Department(AsyncNamespace):
    async def on_connect(self, sid, environ: dict, auth: dict):

        query_string: str = environ.get('QUERY_STRING')
        list_query = query_string.split('&')
        list_session_ids: list = list(filter(lambda str_: str_.__contains__('session_id'), list_query))

        authError = ConnectionRefusedError(
            "Authentication Failed"
        )

        if any([len(list_session_ids) == 0, auth is None]):
            raise authError  # refuse connection if there is no identification

        key = auth.get("Authorization")

        type_, token = key.split(" ") if key is not None else [None, None]
        user_id = auth.get("id_user")

        if any([type_ is None, token is None, user_id is None]):
            raise authError

        key, session_id = list_session_ids[0].split("=")

        is_bson_id(session_id)
        is_bson_id(user_id)

        if session_id is None:
            raise authError

        # session_: dict = await db.get_collection(Collections.SESSION).find_one(
        #     {schemes.Session.ID_: ObjectId(session_id)})

        # if session_ is None or not session_.get(schemes.Session.ISALIVE):
        #     return ConnectionRefusedError(
        #         "Session Expired"
        #     )  # session expired

        try:
            username_from_jwt_token = JWTUtilits.decodeAccessToken(token)
            username = username_from_jwt_token.get("sub")
            if username is None:
                print("No Connection You Are Anonymous")
                return False  # no connection

            user_info = {}
            user_info.update({"username": username.split("@")[0]})
            user_info.update({"user_id": user_id})
            user_info.update({"session_id": session_id})

            await self.save_session(sid, user_info)
            print(username.split("@")[0])
            await self.emit("join", f"{user_info.get('username')} join the session")
            # save message to database
            print(user_info)
            print(MessageType.JOIN)

            await save_message("user join", MessageType.JOIN, user_info.get('user_id'), user_info.get('session_id'))

        except (JWTError, ExpiredSignatureError, JWTClaimsError) as e:
            print(f"There is Problem! {e}")
            raise ConnectionRefusedError(
                "Token Invalid Or Expired"
            )

        return True

    async def on_disconnect(self, sid):
        dict_: dict = await self.get_session(sid)
        await self.emit("onedisconnect", [dict_.get("username")])
        print("There is One Disconnect")

    async def on_message(self, sid, data):
        print("message came".center(50, "-"))
        print(data)
        data_user: dict = await self.get_session(sid)
        username = data_user.get('username')
        user_id = data_user.get('id_user')
        session_id = data_user.get('session_id')

        await self.emit('response', [username, data])
        await save_message(data, MessageType.MESSAGE, user_id, session_id)
        return 'OK', 200

    async def on_discition(self, sid, data):
        data_user: dict = await self.get_session(sid)
        username = data_user.get('username')
        await self.emit('response', f'{username} : DESCITION {data}', skip_sid=sid)


sio.register_namespace(Department(DepartmentNameSpace.MGT_DEPARTMENT))
sio.register_namespace(Department(DepartmentNameSpace.IT_DEPARTMENT))
sio.register_namespace(Department(DepartmentNameSpace.ELECTRICAL_DEPARTMENT))
