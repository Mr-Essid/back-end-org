from enum import Enum, StrEnum


class Collections(StrEnum):
    USER = 'User'
    PROJECT = 'Project'
    DEPARTMENT = 'Department'
    HISTORY_DEPARTMENT = 'History_Department'
    HISTORY_SECURE = 'History_Secure'

    def __str__(self):
        return self.value

