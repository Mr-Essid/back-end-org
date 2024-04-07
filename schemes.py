from enum import StrEnum


class User(StrEnum):
    FULL_NAME = 'fill_name'
    EMAIL = 'email'
    NID = 'nid'
    FACE_CODDING = 'face_coding'
    PASSWORD = 'password'
    ROLE = 'role'
    IS_ACTIVE = 'is_active'
    EMAIL_VERIFIED = 'email_verified'
    CREATE_AT = 'created_at'
    UPDATE_AT = 'update_at'
    ID_DEPARTMENT = 'id_dep'
    ID_ = '_id'


class DepartmentS(StrEnum):
    DEPARTMENT_NAME = 'name_department'
    DEPARTMENT_IDENTIFICATION = 'department_identification'
    CREATE_AT = 'create_at'
    UPDATE_AT = 'update_at'


class Project(StrEnum):
    PROJECT_IDENTIFIER = 'id_project'
    PROJECT_DESCRIPTION = 'description'
    CLIENT_BRAND = 'client_brand'
    CLIENT_LOCATION = 'client_location'
    DEPARTMENT_ID = 'department_identification'
    PROGRESS = 'progress'
    IS_WORKING_ON = 'is_working_on'
    IS_ACTIVE = 'is_active'
    START_AT = 'start_at'
    END_AT = 'end_at'
    CURRENT_STATE = 'current_stat'
    FUNCTIONAL_DELAY = 'functional_delay'
    CREATE_AT = 'create_at'
    UPDATE_AT = 'update_at'


class HistoryDepartmentS(StrEnum):
    EMPLOYER_ID = 'employer_id'
    DEPARTMENT_ID = 'department_id'
    DATE_TIME = 'date_time'


class HistorySecureS(StrEnum):
    MANAGER_ID = 'manager_id'
    DATE_TIME = 'date_time'
