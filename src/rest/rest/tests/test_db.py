from unittest import mock

from django.test import SimpleTestCase
from pymongo.errors import CollectionInvalid, NetworkTimeout, OperationFailure

from rest.db import NAMESPACE_EXISTS, DatabaseError, MongoDB

VALIDATOR = {"$jsonSchema": {"bsonType": "object"}}


class MongoDBTestCase(SimpleTestCase):
    """Replaces pymongo's Database object with a mock. No server is needed."""

    def setUp(self):
        # MongoClient connects lazily, so this does not open a connection.
        self.mongo = MongoDB("mongodb://unused:27017", "test")
        self.db = mock.MagicMock()
        self.collection = self.db.__getitem__.return_value
        self.mongo._db = self.db


class EnsureCollectionTests(MongoDBTestCase):

    def test_creates_a_new_collection_and_its_indexes(self):
        self.mongo.ensure_collection("todos", VALIDATOR, indexes=[[("created_at", -1)]])

        self.db.create_collection.assert_called_once_with("todos", validator=VALIDATOR)
        self.db.command.assert_not_called()
        self.collection.create_index.assert_called_once_with([("created_at", -1)])

    def test_updates_the_validator_when_the_collection_exists(self):
        self.db.create_collection.side_effect = CollectionInvalid("exists")

        self.mongo.ensure_collection("todos", VALIDATOR)

        self.db.command.assert_called_once_with("collMod", "todos", validator=VALIDATOR)

    def test_treats_a_parallel_create_as_exists(self):
        # Another process created the collection after pymongo's own check.
        self.db.create_collection.side_effect = OperationFailure(
            "already exists", code=NAMESPACE_EXISTS
        )

        self.mongo.ensure_collection("todos", VALIDATOR)

        self.db.command.assert_called_once_with("collMod", "todos", validator=VALIDATOR)

    def test_other_server_errors_become_database_error(self):
        self.db.create_collection.side_effect = OperationFailure("denied", code=13)

        with self.assertRaises(DatabaseError):
            self.mongo.ensure_collection("todos", VALIDATOR)


class InsertOneTests(MongoDBTestCase):

    def test_returns_the_new_id_and_does_not_change_the_callers_dict(self):
        self.collection.insert_one.return_value.inserted_id = "new-id"
        document = {"description": "Buy milk"}

        self.assertEqual(self.mongo.insert_one("todos", document), "new-id")
        self.assertEqual(document, {"description": "Buy milk"})

    def test_wraps_pymongo_errors(self):
        self.collection.insert_one.side_effect = NetworkTimeout("timed out")

        with self.assertRaises(DatabaseError) as raised:
            self.mongo.insert_one("todos", {})
        self.assertIsInstance(raised.exception.__cause__, NetworkTimeout)


class FindManyTests(MongoDBTestCase):

    def test_wraps_errors_raised_while_reading_the_cursor(self):
        # A cursor fetches lazily, so the error comes from iteration, not find().
        self.collection.find.return_value.__iter__.side_effect = NetworkTimeout("timed out")

        with self.assertRaises(DatabaseError):
            self.mongo.find_many("todos")

    def test_passes_sort_and_limit_to_pymongo(self):
        self.collection.find.return_value = iter([{"a": 1}])

        result = self.mongo.find_many("todos", sort=[("created_at", -1)], limit=5)

        self.assertEqual(result, [{"a": 1}])
        self.collection.find.assert_called_once_with({}, sort=[("created_at", -1)], limit=5)
