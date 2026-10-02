"""Data access for TODOs. Wrapper between the Todos collection (MongoDB) and todos within python.

The repository converts between `Todo` objects and Mongo documents. Views
work with `Todo` objects only and do not know collection names or queries.

Handles everything an outer caller would want to do with a todo, abstracted away from the details
of how that is done.
"""
from functools import lru_cache
from typing import List

from .db import MongoDB, get_mongo
from .todo_schema import NEWEST_FIRST, TODO_COLLECTION, TODO_INDEXES, TODO_VALIDATOR, Todo

# Upper limit on how many TODOs one list call returns, so that a large
# collection cannot make a response unbounded. Pagination is the next step
# if the list must show more than this.
LIST_LIMIT = 500


class TodoRepository:
    def __init__(self, mongo: MongoDB) -> None:
        # The constructor does no I/O. A test can pass in a fake MongoDB.
        self._mongo = mongo

    def ensure_schema(self) -> None:
        """Create the collection, validator and indexes. Safe to call many times.

        Raises DatabaseError.
        """
        self._mongo.ensure_collection(
            TODO_COLLECTION, validator=TODO_VALIDATOR, indexes=TODO_INDEXES
        )

    def list_all(self) -> List[Todo]:
        """Return the newest TODOs (at most LIST_LIMIT), newest first.

        Raises DatabaseError.
        """
        documents = self._mongo.find_many(
            TODO_COLLECTION, sort=NEWEST_FIRST, limit=LIST_LIMIT
        )
        return [Todo.from_document(document) for document in documents]

    def add(self, todo: Todo) -> Todo:
        """Save a new TODO and return it with its id. Raises DatabaseError."""
        # Save todo, get new id, update todo id, return todo
        new_id = self._mongo.insert_one(TODO_COLLECTION, todo.to_document())
        return todo.with_id(new_id)


@lru_cache(maxsize=None)
def get_todo_repository() -> TodoRepository:
    """Return the shared repository. The first call sets up the collection.

    Raises DatabaseError if Mongo is down. `lru_cache` does not cache an
    exception, so the next request tries the setup again.
    """
    mongo = get_mongo() # Get a db instance
    repository = TodoRepository(mongo)
    repository.ensure_schema()
    return repository
