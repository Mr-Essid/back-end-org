"""
    This is our history model
    context:
        all history with in our system is submitted by raspberry pi which is our edge in our system architecture that's mean!

        we have our department include employers:
            employers of specific department can access there department to work
            department manager can access Place A!
"""
import datetime
import json

from bson import ObjectId
from pydantic import BaseModel, model_validator

"""
    actions:
        READ
        WRITE    
        access:
            READ: Employer
            WRITE: RaspberryPi
        
"""


class HistoryDepartment(BaseModel):
    employer_id: str  # will be our ObjectId
    department_id: str  # this is not a fault we know all that we can access this man from the employer but this is optimization that will help us improve our fetch by department, thank you!
    date_: datetime.date
    time_: datetime.time

    """
        We missed this in older models, but it has been corrected in the controller.
    """

    @model_validator(mode='before')
    @classmethod
    def check_of_employer_id_valid_objectid(cls, data):
        if not ObjectId.is_valid(data.employer_id):
            raise ValueError('Incorrect Employer Id, Same Thing Went Wrong')
        return data


"""
    access:
        write: RaspberryPi
        read:  Admin
"""


class HistorySecure(BaseModel):
    """
        in this point we can add raison to enter place
    """
    manager_id: str
    date_: datetime.date
    time_: datetime.date

    @model_validator(mode='before')
    @classmethod
    def check_of_employer_id_valid_objectid(cls, data):
        if not ObjectId.is_valid(data.manager_id):
            raise ValueError('Incorrect Manager Id, Same Thing Went Wrong')
        return data


if __name__ == '__main__':
    with open('./history_department.json', 'w') as file:
        json_ = HistoryDepartment.model_json_schema()
        json.dump(json_, indent=2, fp=file)

    with open('./history_secure.json', 'w') as file:
        json_ = HistorySecure.model_json_schema()
        json.dump(json_, indent=2, fp=file)
