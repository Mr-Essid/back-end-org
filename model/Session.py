import datetime
import json
from enum import StrEnum

from bson import ObjectId
from pydantic import BaseModel, Field, model_validator


class SessionState(StrEnum):
    ACTIVE = 'active'
    DIS_ACTIVE = 'dis-active'


class DepartmentEndPoint(StrEnum):
    ELECTRIC = 'ELECTRIC'
    IT = 'IT'
    MGT = 'MGT'


class SessionRequest(BaseModel):
    isAlive: bool = False
    isOnline: bool = True
    beginAt: datetime.datetime
    estimatedTimeInHours: int
    projectId: str
    description: str


class SessionResponseBefore(SessionRequest):
    dIdentification: int
    dEndpoint: str
    managerDeclareId: str
    isDone: bool = False
    created_at: datetime.datetime
    updated_at: datetime.datetime


class SessionResponseAfter(SessionResponseBefore):
    id_: str = Field(alias="_id")


class SessionUpdate(BaseModel):
    id_: str = Field(alias="_id")
    beginAt: datetime.datetime | None = None
    estimatedTimeInHours: int | None = None
    description: str | None = None

    @model_validator(mode='before')
    @classmethod
    def at_least_one(cls, data):
        if not ObjectId.is_valid(data['_id']):
            raise ValueError(
                'id not valid'
            )

        for k, v in data.items():
            if k != '_id' and v is not None:
                return data

        raise ValueError(
            'at least you have to supply one element to update'
        )


if __name__ == '__main__':
    """
        here we go session is the basic unit of communication
        actions:
            create, update, delete: access manager
            read: Employers
    """

    with open('./sessionSchema.json', mode='w') as json_file:
        json.dump(SessionResponseBefore.model_json_schema(), indent=2, fp=json_file)
