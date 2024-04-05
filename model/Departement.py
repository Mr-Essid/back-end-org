import datetime

from pydantic import BaseModel


class Department(BaseModel):
    name_department: str
    department_identification: int
    create_at: datetime.datetime
    update_at: datetime.datetime





