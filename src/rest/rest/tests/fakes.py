"""In-memory stand-in for `rest.db.MongoDB`, for tests that need no server."""
from collections import defaultdict

from bson import ObjectId
from pymongo import DESCENDING

from rest.db import DatabaseError


class FakeMongo:
    """Same public methods as MongoDB. Set `fail = True` to simulate an outage."""

    def __init__(self):
        self.collections = defaultdict(list)
        self.ensured = []
        self.fail = False

    def _check(self):
        if self.fail:
            raise DatabaseError("simulated outage")

    def insert_one(self, collection, document):
        self._check()
        stored = dict(document, _id=ObjectId())
        self.collections[collection].append(stored)
        return str(stored["_id"])

    def find_many(self, collection, query=None, sort=None, limit=0):
        self._check()
        documents = list(self.collections[collection])
        # Sort by the last key first, so that the first key wins (stable sort).
        for key, direction in reversed(sort or []):
            documents.sort(key=lambda d: d[key], reverse=direction == DESCENDING)
        return documents[:limit] if limit else documents

    def ensure_collection(self, collection, validator, indexes=()):
        self._check()
        self.ensured.append(collection)
