from datetime import datetime, timedelta, timezone
from unittest import mock

from rest_framework.test import APISimpleTestCase

from rest import todo_repository
from rest.db import DatabaseError
from rest.todo_repository import TodoRepository
from rest.todo_schema import DESCRIPTION_MAX_LENGTH, TODO_COLLECTION, Todo

from .fakes import FakeMongo

URL = "/todos/"


class TodoApiTestCase(APISimpleTestCase):
    """Runs the real views, repository and error handler on a FakeMongo."""

    def setUp(self):
        self.mongo = FakeMongo()
        self.repository = TodoRepository(self.mongo)
        patcher = mock.patch("rest.views.get_todo_repository", return_value=self.repository)
        patcher.start()
        self.addCleanup(patcher.stop)

    def add_stored_todo(self, description, created_at):
        self.repository.add(Todo(description=description, created_at=created_at))


class ListTodosTests(TodoApiTestCase):

    def test_empty_list(self):
        response = self.client.get(URL)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"todos": []})

    def test_returns_newest_first(self):
        now = datetime.now(timezone.utc)
        self.add_stored_todo("older", now - timedelta(minutes=1))
        self.add_stored_todo("newer", now)

        todos = self.client.get(URL).json()["todos"]

        self.assertEqual([todo["description"] for todo in todos], ["newer", "older"])
        self.assertEqual(set(todos[0]), {"id", "description", "created_at"})

    def test_returns_at_most_the_list_limit(self):
        now = datetime.now(timezone.utc)
        for i in range(3):
            self.add_stored_todo(f"todo {i}", now + timedelta(seconds=i))

        with mock.patch("rest.todo_repository.LIST_LIMIT", 2):
            todos = self.client.get(URL).json()["todos"]

        self.assertEqual([todo["description"] for todo in todos], ["todo 2", "todo 1"])

    def test_url_without_trailing_slash_redirects(self):
        # The route is `todos/`. Django's APPEND_SLASH redirects a GET. Clients
        # must POST to `/todos/`: Django cannot redirect a POST with its body.
        response = self.client.get("/todos")
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "/todos/")


class CreateTodoTests(TodoApiTestCase):

    def post(self, data, url=URL, **kwargs):
        return self.client.post(url, data, format="json", **kwargs)

    def test_creates_a_todo(self):
        response = self.post({"description": "  Buy milk  "})

        self.assertEqual(response.status_code, 201)
        todo = response.json()["todo"]
        self.assertEqual(todo["description"], "Buy milk")
        stored = self.mongo.collections[TODO_COLLECTION]
        self.assertEqual(len(stored), 1)
        self.assertEqual(str(stored[0]["_id"]), todo["id"])

    def test_ignores_unknown_fields(self):
        self.post({"description": "Buy milk", "admin": True})

        self.assertNotIn("admin", self.mongo.collections[TODO_COLLECTION][0])

    def test_rejects_invalid_descriptions(self):
        cases = {
            "missing": {},
            "not a string": {"description": 123},
            "empty": {"description": ""},
            "only spaces": {"description": "   "},
            "too long": {"description": "x" * (DESCRIPTION_MAX_LENGTH + 1)},
        }
        for name, data in cases.items():
            with self.subTest(name):
                response = self.post(data)
                self.assertEqual(response.status_code, 400)
                self.assertIn("detail", response.json())
        self.assertEqual(self.mongo.collections[TODO_COLLECTION], [])

    def test_rejects_a_body_that_is_not_an_object(self):
        response = self.post(["Buy milk"])

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Request body must be a JSON object."})

    def test_rejects_malformed_json(self):
        response = self.client.post(URL, '{"description":', content_type="application/json")

        self.assertEqual(response.status_code, 400)


class ErrorHandlingTests(TodoApiTestCase):

    def test_database_outage_gives_503_on_get_and_post(self):
        self.mongo.fail = True
        requests = {
            "GET": lambda: self.client.get(URL),
            "POST": lambda: self.client.post(URL, {"description": "x"}, format="json"),
        }
        for method, send in requests.items():
            with self.subTest(method), self.assertLogs("rest.exceptions", "ERROR"):
                response = send()
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json(), {
                    "detail": "The database is unavailable. Try again later."
                })

    def test_unexpected_error_gives_json_500(self):
        with mock.patch.object(self.repository, "list_all", side_effect=RuntimeError("bug")), \
                self.assertLogs("rest.exceptions", "ERROR") as logs:
            response = self.client.get(URL)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": "Something went wrong on the server."})
        self.assertIn("RuntimeError: bug", "\n".join(logs.output))


class RepositoryFactoryTests(APISimpleTestCase):

    def test_setup_failure_is_not_cached(self):
        mongo = FakeMongo()
        mongo.fail = True
        todo_repository.get_todo_repository.cache_clear()
        self.addCleanup(todo_repository.get_todo_repository.cache_clear)

        with mock.patch.object(todo_repository, "get_mongo", return_value=mongo):
            with self.assertRaises(DatabaseError):
                todo_repository.get_todo_repository()
            mongo.fail = False  # Mongo comes back.
            repository = todo_repository.get_todo_repository()

        self.assertIsInstance(repository, TodoRepository)
        self.assertEqual(mongo.ensured, [TODO_COLLECTION])
