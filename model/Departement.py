import datetime
import json

from pydantic import BaseModel
from utiles import IS_PROTECTION


class Department(BaseModel):
    name_department: str
    department_identification: int
    create_at: datetime.datetime
    update_at: datetime.datetime


if __name__ == '__main__':
    if not IS_PROTECTION:
        with open('./departmentSchema.json', mode='w') as file:
            json_ = Department.model_json_schema()
            json.dump(json_, indent=2, fp=file)




