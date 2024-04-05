import datetime

from pydantic import BaseModel, model_validator, Field
from enum import StrEnum


class State(StrEnum):
    PLANNING = 'planing'
    IMPLEMENTING = 'implementing'
    TESTING = 'testing'


class Project(BaseModel):
    description: str
    client_brand: str = Field(max_length=64)
    client_location: str = Field(max_length=64)
    start_at: datetime.datetime
    end_at: datetime.datetime
    create_at: datetime.datetime
    update_at: datetime.datetime

    # optional params
    progress: int = Field(default=0, le=100, ge=0)
    is_working_on: bool = Field(default=True)
    is_active: bool = Field(default=True)
    functional_delay: datetime.timedelta = Field(default=datetime.timedelta(days=2))
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



if __name__ == '__main__':
    with open('./projectJsonSchema.json', mode='w') as json_file:
        json_file.write(ProjectResponse.model_json_schema().__str__())
