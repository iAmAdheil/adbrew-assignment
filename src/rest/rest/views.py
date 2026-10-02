from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.response import Response
from rest_framework.views import APIView

from .todo_repository import get_todo_repository
from .todo_schema import Todo

# The views do not catch errors. DRF's APIView.dispatch() catches every
# exception and calls rest.exceptions.api_exception_handler (set in settings):
#   InvalidTodo   -> 400
#   DatabaseError -> 503
# Any error thrown from inside controllers, helpers
# handled by DRF handler


class TodoListView(APIView):

    def get(self, request):
        todos = get_todo_repository().list_all()
        return Response(
            {"todos": [todo.to_dict() for todo in todos]},
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        # A JSON body such as `[]` or `"text"` is valid JSON but not an object.
        if not isinstance(request.data, dict):
            raise ParseError("Request body must be a JSON object.")
        todo = Todo.new(request.data.get("description"))
        saved = get_todo_repository().add(todo)
        return Response({"todo": saved.to_dict()}, status=status.HTTP_201_CREATED)
