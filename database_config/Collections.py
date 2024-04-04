from enum import Enum, StrEnum


class Collections(StrEnum):
    USER = 'User'
    PROJECT = 'Project'
    DEPARTMENT = 'Department'

    def __str__(self):
        return self.value

