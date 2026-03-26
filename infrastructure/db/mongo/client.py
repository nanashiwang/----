from __future__ import annotations

from pymongo import MongoClient


class MongoClientManager:
    def __init__(self, uri: str, db_name: str):
        self._client = MongoClient(uri)
        self._db = self._client[db_name]

    @property
    def db(self):
        return self._db

    def get_collection(self, name: str):
        return self._db[name]
