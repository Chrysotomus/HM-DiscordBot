import asyncio
import motor.motor_asyncio
from abc import ABC, abstractmethod


class MongoDocument(ABC):
    @abstractmethod
    @property
    def document(self):
        pass


# noinspection PyTypeChecker,PyUnresolvedReferences
class MongoCollection(ABC):
    def __init__(self, client: motor.motor_asyncio.AsyncIOMotorClient, database: str, collection: str):
        self.collection: motor.motor_asyncio.AsyncIOMotorCollection = client[database][collection]

    @abstractmethod
    async def insert_one(self, document: dict):
        pass

    # @abstractmethod
    # async def insert_many(self, documents: list[dict]):
    #     return await self.collection.insert_many(documents)

    @abstractmethod
    async def find_one(self, find_params: dict):
        pass

    @abstractmethod
    async def find(self, find_params: dict, sort: dict = None, limit: int = None):
        pass

    @abstractmethod
    async def update_one(self, find_params: dict, replace: dict):
        pass

    # @abstractmethod
    # async def update_many(self, find_params: dict, replace: dict):
    #     await self.collection.update_many(find_params, {"$set": replace})

    @final
    async def delete_one(self, document: MongoDocument):
        await self.collection.delete_one(document.document)

    @final
    async def delete_many(self, find_params: dict):
        await self.collection.delete_many(find_params)