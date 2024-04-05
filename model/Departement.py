import datetime

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
            file.write(Department.model_json_schema().__str__())





