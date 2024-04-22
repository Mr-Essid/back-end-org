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
    employer_name: str  # we know that we can query the employer name from the id of it but but you have to pay attention here cause if you will display the message you have to query the user table to get the name !! it's fucking fault
    date_time: datetime.datetime


class MessageResponse(Message):
    id_: str = Field(alias="_id")


if __name__ == '__main__':
    with open('./message.json', 'w') as file:
        json_ = Message.model_json_schema()
        json.dump(json_, indent=2, fp=file)
