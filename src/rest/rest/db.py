"""MongoDB access.

`MongoDB` is the only class that talks to pymongo. Other modules call its
methods and catch `DatabaseError`. They do not import pymongo themselves.

Interacts with respective entity wrappers. Ensures schemas/ collections do exist
and run queries on those collections.
"""
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence, Tuple

from pymongo import MongoClient
from pymongo.errors import CollectionInvalid, OperationFailure, PyMongoError

# Fail fast when Mongo is down, instead of the 30s pymongo default.
SERVER_SELECTION_TIMEOUT_MS = 5000
# Time limit to open a TCP connection to Mongo.
CONNECT_TIMEOUT_MS = 5000
# Time limit to wait for the reply to one operation. The pymongo default is
# no limit, so a Mongo that hangs (but is not down) would block a request forever.
SOCKET_TIMEOUT_MS = 10000
DEFAULT_DB = "test_db"
# Server error code when a collection already exists.
NAMESPACE_EXISTS = 48

Document = Dict[str, Any]
SortSpec = Sequence[Tuple[str, int]]


class DatabaseError(Exception):
    """A Mongo operation failed (server down, timeout, validation error, ...)."""


class MongoDB:
    def __init__(self, uri: str, db_name: str,
                 timeout_ms: int = SERVER_SELECTION_TIMEOUT_MS) -> None:
        # MongoClient connects lazily and keeps its own thread-safe connection
        # pool, so one instance can serve every request in the process.
        self._client = MongoClient(
            uri,
            # Return datetimes with tzinfo=UTC instead of naive datetimes.
            tz_aware=True,
            serverSelectionTimeoutMS=timeout_ms,
            connectTimeoutMS=CONNECT_TIMEOUT_MS,
            socketTimeoutMS=SOCKET_TIMEOUT_MS,
        )
        self._db = self._client[db_name]

    @classmethod
    def from_env(cls) -> "MongoDB":
        uri = f"mongodb://{os.environ['MONGO_HOST']}:{os.environ['MONGO_PORT']}"
        return cls(uri, os.environ.get("MONGO_DB_NAME", DEFAULT_DB))

    def insert_one(self, collection: str, document: Document) -> str:
        """Insert a document and return its new `_id` as a string."""
        try:
            # pymongo adds `_id` to the dict it gets. Pass a copy so the
            # caller's dict does not change.
            result = self._db[collection].insert_one(dict(document))
        except PyMongoError as exc:
            raise DatabaseError(f"insert into '{collection}' failed") from exc
        return str(result.inserted_id)

    def find_many(self, collection: str, query: Optional[Document] = None,
                  sort: Optional[SortSpec] = None, limit: int = 0) -> List[Document]:
        """Return the matching documents. `limit=0` means no limit."""
        try:
            cursor = self._db[collection].find(query or {}, sort=sort, limit=limit)
            # A cursor reads from the server only when iterated. Read it here so
            # that network errors raise inside this try block.
            return list(cursor)
        except PyMongoError as exc:
            raise DatabaseError(f"query on '{collection}' failed") from exc

    def ensure_collection(self, collection: str, validator: Document,
                          indexes: Sequence[SortSpec] = ()) -> None:
        """Create the collection with a validator and indexes. Safe to call many times."""
        try:
            if not self._create_collection(collection, validator):
                # The collection exists. Update its validator in case the schema changed.
                self._db.command("collMod", collection, validator=validator)
            for keys in indexes:
                self._db[collection].create_index(list(keys))
        except PyMongoError as exc:
            raise DatabaseError(f"setup of '{collection}' failed") from exc

    def _create_collection(self, collection: str, validator: Document) -> bool:
        """Create the collection. Return False if it already exists."""
        try:
            self._db.create_collection(collection, validator=validator)
        except CollectionInvalid:
            # pymongo checked the collection list first and found the name.
            return False
        except OperationFailure as exc:
            # Another thread or process created the collection between
            # pymongo's check and the server's create command.
            if exc.code != NAMESPACE_EXISTS:
                raise
            return False
        return True

    def close(self) -> None:
        self._client.close()


@lru_cache(maxsize=None)
def get_mongo() -> MongoDB:
    """Return the shared MongoDB instance for this process."""
    return MongoDB.from_env()
