from enum import StrEnum


class User(StrEnum):
    FULL_NAME = 'fill_name'
    EMAIL = 'email'
    NID = 'nid'
    PASSWORD = 'password'
    ROLE = 'role'
    AUTHORITIES = 'authorities'
    IS_ACTIVE = 'is_active'
    EMAIL_VERIFIED = 'email_verified'
    CREATE_AT = 'created_at'
    UPDATE_AT = 'update_at'
    ID_ = '_id'
