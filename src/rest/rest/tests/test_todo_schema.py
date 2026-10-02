from datetime import datetime, timezone

from bson import ObjectId
from django.test import SimpleTestCase

from rest.todo_schema import DESCRIPTION_MAX_LENGTH, TODO_VALIDATOR, InvalidTodo, Todo

NOW = datetime(2026, 10, 2, 6, 0, 0, 123000, tzinfo=timezone.utc)


class TodoNewTests(SimpleTestCase):

    def test_trims_the_description(self):
        self.assertEqual(Todo.new("  Buy milk  ").description, "Buy milk")

    def test_sets_a_utc_timestamp_cut_to_milliseconds(self):
        created_at = Todo.new("Buy milk").created_at
        self.assertEqual(created_at.tzinfo, timezone.utc)
        self.assertEqual(created_at.microsecond % 1000, 0)

    def test_has_no_id_before_it_is_saved(self):
        self.assertIsNone(Todo.new("Buy milk").id)

    def test_accepts_the_maximum_length(self):
        todo = Todo.new("x" * DESCRIPTION_MAX_LENGTH)
        self.assertEqual(len(todo.description), DESCRIPTION_MAX_LENGTH)

    def test_rejects_invalid_descriptions(self):
        cases = {
            "not a string": 123,
            "missing": None,
            "empty": "",
            "only spaces": "   ",
            "too long": "x" * (DESCRIPTION_MAX_LENGTH + 1),
        }
        for name, description in cases.items():
            with self.subTest(name), self.assertRaises(InvalidTodo):
                Todo.new(description)


class TodoInvariantTests(SimpleTestCase):

    def test_direct_construction_is_also_validated(self):
        with self.assertRaises(InvalidTodo):
            Todo(description="", created_at=NOW)

    def test_rejects_a_naive_created_at(self):
        with self.assertRaises(TypeError):
            Todo(description="Buy milk", created_at=datetime(2026, 10, 2))


class TodoConversionTests(SimpleTestCase):

    def test_document_round_trip(self):
        object_id = ObjectId()
        document = {"_id": object_id, "description": "Buy milk", "created_at": NOW}

        todo = Todo.from_document(document)

        self.assertEqual(todo.id, str(object_id))
        self.assertEqual(todo.to_document(), {"description": "Buy milk", "created_at": NOW})

    def test_to_dict_is_json_safe(self):
        todo = Todo(description="Buy milk", created_at=NOW, id="abc")
        self.assertEqual(todo.to_dict(), {
            "id": "abc",
            "description": "Buy milk",
            "created_at": "2026-10-02T06:00:00.123000+00:00",
        })

    def test_with_id_returns_a_copy(self):
        todo = Todo(description="Buy milk", created_at=NOW)
        saved = todo.with_id("abc")
        self.assertEqual(saved.id, "abc")
        self.assertIsNone(todo.id)


class ValidatorTests(SimpleTestCase):

    def test_mongo_validator_uses_the_same_length_limit(self):
        description_rule = TODO_VALIDATOR["$jsonSchema"]["properties"]["description"]
        self.assertEqual(description_rule["maxLength"], DESCRIPTION_MAX_LENGTH)
