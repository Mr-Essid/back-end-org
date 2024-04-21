import json
from enum import StrEnum
import datetime
from bson import ObjectId
from pydantic import BaseModel, model_validator, Field


class MessageType(StrEnum):
    JOIN = "join"
    MESSAGE = "message"
    DISCONNECT = "disconnect"
    DECISION = "decision"


class Message(BaseModel):
    message_content: str
    type_: MessageType
    employer_id: str
    session_id: str
    date_time: datetime.datetime




class MessageResponse(Message):
    id_: str = Field(alias="_id")


if __name__ == '__main__':
    with open('./message.json', 'w') as file:
        json_ = Message.model_json_schema()
        json.dump(json_, indent=2, fp=file)



