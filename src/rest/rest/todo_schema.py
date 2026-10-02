"""Shape of a TODO, in Python, in MongoDB, and in the API response.

Stored document in the `todos` collection:

    {
        "_id": ObjectId("..."),
        "description": "Buy milk",       # 1..500 characters
        "created_at": ISODate("...")     # UTC, set by the server
    }
"""
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pymongo import DESCENDING

TODO_COLLECTION = "todos"
DESCRIPTION_MAX_LENGTH = 500

NEWEST_FIRST = [("created_at", DESCENDING)]  # set sort order
TODO_INDEXES = [NEWEST_FIRST]  # indexes to be created in collection

# Last line of defence: Mongo rejects any insert or update that does not
# match this shape, even if it does not come through the API
TODO_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["description", "created_at"],
        "additionalProperties": False,
        "properties": {
            "_id": {"bsonType": "objectId"},
            "description": {
                "bsonType": "string",
                "minLength": 1,
                "maxLength": DESCRIPTION_MAX_LENGTH,
            },
            "created_at": {"bsonType": "date"},
        },
    }
}


def _utc_now_millis() -> datetime:
    """Current UTC time, cut to milliseconds.

    BSON dates store milliseconds only. Without the cut, the POST response
    would show microseconds that a later GET of the same TODO does not.
    """
    now = datetime.now(timezone.utc)
    return now.replace(microsecond=now.microsecond // 1000 * 1000)


class InvalidTodo(ValueError):
    """Data that cannot form a valid Todo. The API returns it as a 400."""


@dataclass(frozen=True)
class Todo:
    description: str
    created_at: datetime
    id: Optional[str] = None  # None until Mongo assigns an _id.

    def __post_init__(self) -> None:
        """Check the invariants. Every way of creating a Todo runs this."""
        # Validate once fields are populated
        # The messages go to the user (API 400 response), so they are sentences.
        if not isinstance(self.description, str):
            raise InvalidTodo("The description must be text.")
        if not self.description.strip():
            raise InvalidTodo("Enter a description.")
        if len(self.description) > DESCRIPTION_MAX_LENGTH:
            raise InvalidTodo(
                f"The description must be at most {DESCRIPTION_MAX_LENGTH} characters."
            )
        # The server sets created_at, so a bad value is a bug, not bad user
        # input. TypeError gives a 500, not a 400.
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise TypeError("created_at must be a timezone-aware datetime")

    @classmethod
    def new(cls, description: Any) -> "Todo":
        """Create a Todo from user input. Raises InvalidTodo."""
        # Trim here, not in __post_init__: a frozen dataclass cannot change its
        # own fields, and trimming is input cleanup, not an invariant.
        if isinstance(description, str):
            description = description.strip()
        return cls(description=description, created_at=_utc_now_millis())

    def with_id(self, id: str) -> "Todo":
        """Return a copy with the `_id` that Mongo assigned."""
        return replace(self, id=id)

    @classmethod
    def from_document(cls, document: Dict[str, Any]) -> "Todo":
        return cls(
            id=str(document["_id"]),
            description=document["description"],
            created_at=document["created_at"],
        )

    def to_document(self) -> Dict[str, Any]:
        """Fields to insert. Mongo generates `_id`."""
        return {"description": self.description, "created_at": self.created_at}

    def to_dict(self) -> Dict[str, Any]:
        """JSON-safe representation for API responses."""
        return {
            "id": self.id,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
        }
