from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from starlette import status

import schemes
from database_config.Collections import Collections
from database_config.configdb import db
from model.Employer import Roles
from model.Message import MessageResponse
from route.login_route import get_current_user
from utiles import from_bson, is_bson_id

messageRoute = APIRouter(prefix="/message")


@messageRoute.get("/{session_id}")
async def get_message_of_session(session_id: str, current_user: dict = Depends(get_current_user)):
    session = await db.get_collection(Collections.SESSION).find_one({schemes.Session.ID_: ObjectId(session_id)})

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"There is No Session With Id {session_id}"
        )

    if schemes.Session.D_ID != current_user.get(schemes.User.ID_DEPARTMENT) and current_user.get(
            schemes.User.ROLE) != Roles.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access Forbidden for this resource"
        )
    message_list = await db.get_collection(Collections.MESSAGE).find({schemes.Message.SESSION_ID: session_id}).sort(
        {schemes.Message.DATE_TIME: 1}).to_list(None)

    python_message_list = list(map(lambda item: from_bson(item, MessageResponse), message_list))
    return python_message_list


@messageRoute.delete("/{message_id}")
async def delete_message(message_id: str, current_user: dict = Depends(get_current_user)):
    is_bson_id(message_id)
    message = await db.get_collection(Collections.MESSAGE).find_one({schemes.Message.ID_: ObjectId(message_id)})
    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message Not Exits"
        )

    if message.get(schemes.Message.EMPLOYER_ID) != current_user.get(schemes.User.ID_):
        raise HTTPException(
            detail="Access Forbidden For This Specific Resource",
            status_code=status.HTTP_403_FORBIDDEN
        )

    deleted = await db.get_collection(Collections.MESSAGE).delete_one({schemes.Message.ID_: ObjectId(message_id)})
    return {
        "status": "Message Deleted"
    }
