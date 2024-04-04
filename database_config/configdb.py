from motor.motor_asyncio import AsyncIOMotorClient
from env import load_env


class SuperDatabase:
    pass


class Database:
    instance = None

    def __new__(cls):
        USERNAME, PASSWORD, HOST, APP_NAME, DATABASE = load_env()
        if cls.instance is None:
            __URI = f'mongodb+srv://{USERNAME}:{PASSWORD}@{APP_NAME}.{HOST}/?retryWrites=true&w=majority&appName={APP_NAME}'
            cls.instance = AsyncIOMotorClient(__URI).get_database(DATABASE)
        return cls.instance


db = Database()



