import datetime
import json
from typing import Optional, Annotated, Union
from enum import Enum, StrEnum
from pydantic import BaseModel, EmailStr, ConfigDict, AfterValidator, PlainSerializer, WithJsonSchema, model_validator, \
    field_validator
from pydantic.fields import Field
from bson.objectid import ObjectId
from typing import Any
from pydantic_core import core_schema

from schemes import User


def validate_object_id(v: Any) -> ObjectId:
    if isinstance(v, ObjectId):
        return v
    if ObjectId.is_valid(v):
        return ObjectId(v)
    raise ValueError("Invalid ObjectId")


PyObjectId = Annotated[
    Union[str, ObjectId],
    AfterValidator(validate_object_id),
    PlainSerializer(lambda x: str(x), return_type=str),
    WithJsonSchema({"type": "string"}, mode="serialization"),
]


class Roles(StrEnum):
    EMPLOYER = 'EMPLOYER'
    ADMIN = 'ADMIN'
    D_MANAGER = 'DEPARTMENT_MANAGER'


class EmployerRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    full_name: str = Field(max_length=40)
    email: EmailStr = Field(max_length=100)
    nid: str = Field(max_length=8)
    password: str
    role: Optional[Roles] = Field(default=Roles.EMPLOYER, to_upper=True)
    is_active: bool = True
    email_verified: bool = False
    face_coding: list[float] | None = None
    id_dep: int

    def __dict__(self):
        return {
            'full_name': self.full_name,
            'email': self.email,
            'nid': self.nid,
            'password': self.password,
            'role': self.role,
            'authorities': self.authorities,
            'is_active': self.is_active,
            'id_dep': self.id_dep,
            'email_verified': self.email_verified,
            'create_at': self.create_at,
            'updated_at': self.update_at
        }

    @classmethod
    def atLeastOne_(cls, data: dict):
        for k, v in data.items():

            if k == User.ID_DEPARTMENT:
                if v not in [1, 2, 3]:
                    raise ValueError('No Specific Department Assigned')

        return data


class EmployerResponse(EmployerRequest):
    id_: PyObjectId = Field(alias='_id')
    model_config = ConfigDict(arbitrary_types_allowed=True)
    create_at: datetime.datetime
    update_at: datetime.datetime

    # def __dict__(self):
    #     super().__dict__().update({'_id': self.id_})


class EmployerUpdate(BaseModel):
    full_name: str | None = None


class EmployerUpdatePrivate(BaseModel):
    id_: str = Field(alias='_id')
    uid: str | None = None
    is_active: bool | None = None

    @classmethod
    def atLeastOne_(cls, data: dict):
        isThereIsOne = False
        for k, v in data.items():
            if v is not None and k != '_id':
                isThereIsOne = True

        if not isThereIsOne:
            raise ValueError('At Least one Attribute to Update')
        return data


class UpdatePassword(BaseModel):
    old_password: str
    new_password: str


class UpgradeEmployer(BaseModel):
    employer_id: str
    department_id: int
    face_coding: list[float]


if __name__ == '__main__':
    with open('employerSchema.json', mode='w') as json_file:
        json_ = EmployerResponse.model_json_schema()
        json.dump(json_, indent=2, fp=json_file)
