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

    @model_validator(mode="before")
    @classmethod
    def validator(cls, data: dict):
        employer_id = data.get('employer_id')
        session_id = data.get('session_id')

        if not ObjectId.is_valid(employer_id):
            raise ValueError(
                "Employer Id is Invalid"
            )

        if not ObjectId.is_valid(session_id):
            raise ValueError(
                "Session Id is Invalid"
            )


class MessageResponse(Message):
    id_: str = Field(alias="_id")


if __name__ == '__main__':
    with open('./message.json', 'w') as file:
        json_ = Message.model_json_schema()
        json.dump(json_, indent=2, fp=file)



