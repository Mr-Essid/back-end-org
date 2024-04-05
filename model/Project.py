import datetime

from pydantic import BaseModel, Field, model_validator
from enum import StrEnum

from utiles import get_filled_only


class State(StrEnum):
    PLANNING = 'planing'
    IMPLEMENTING = 'implementing'
    TESTING = 'testing'


class Project(BaseModel):
    description: str
    client_brand: str = Field(max_length=64)
    client_location: str = Field(max_length=64)
    department_identification: int = Field(le=3, ge=1)  # This Field Take How Many Department Do We Have !!!
    start_at: datetime.datetime
    end_at: datetime.datetime
    create_at: datetime.datetime
    update_at: datetime.datetime
    # optional params
    progress: int = Field(default=0, le=100, ge=0)
    is_working_on: bool = Field(default=True)
    is_active: bool = Field(default=True)
    functional_delay: int = Field(default=datetime.timedelta(days=2))
    state: State = Field(default=State.PLANNING)


"""
class Project(StrEnum):
    PROJECT_IDENTIFIER = 'id_project'
    PROJECT_DESCRIPTION = 'description'
    CLIENT_BRAND = 'client_brand'
    CLIENT_LOCATION = 'client_location'
    PROGRESS = 'progress'
    IS_WORKING_ON = 'is_working_on'
    IS_ACTIVE = 'is_active'
    START_AT = 'start_at'
    END_AT = 'end_at'
    CURRENT_STATE = 'current_stat'
    FUNCTIONAL_DELAY = 'functional_delay'
    CREATE_AT = 'create_at'
    UPDATE_AT = 'update_at'
"""


class ProjectResponse(Project):
    id_: str = Field(alias='_id')


class ProjectUpdate(BaseModel):
    id_: str = Field(alias='_id')
    description: str | None = None
    client_location: str | None = None
    start_at: datetime.datetime | None = None
    end_at: datetime.datetime | None = None

    @model_validator(mode='before')
    @classmethod
    def at_least_one(cls, data):
        data = get_filled_only(data)

        if len(data) == 0:
            raise ValueError('At Least One Property to Update')

        return data


class ProjectFU(BaseModel):
    id_: str = Field(alias='_id')
    progress: int | None = Field(default=None,le=100, ge=1)
    state: State | None = None
    is_working_on: bool | None = None

    @model_validator(mode='before')
    @classmethod
    def at_least_one(cls, data):
        if len(get_filled_only(data)) == 0:
            raise ValueError('At Least One Property to Update')

        return data


if __name__ == '__main__':
    """
        model actions:
        CRUD:
            simple actions, delete it's just soft delete
        O.Action:
            add_progress 
            change_current_state ( planing, implementing, testing )
            is_working_on
    """

    with open('./projectJsonSchema.json', mode='w') as json_file:
        json_file.write(ProjectResponse.model_json_schema().__str__())
