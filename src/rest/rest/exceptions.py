"""API error responses.

DRF calls `api_exception_handler` for every exception that a view raises.
Views do not need their own try/except blocks for database failures.
"""
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from .db import DatabaseError
from .todo_schema import InvalidTodo

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    # DRF handles its own exceptions (validation errors, 404, 405, ...).
    response = exception_handler(exc, context)
    if response is not None:
        return response

    if isinstance(exc, InvalidTodo):
        # The client sent bad data. The message says what to fix.
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    if isinstance(exc, DatabaseError):
        # Log the full cause for us. Send a generic message to the client.
        logger.error("Database error in %s", context["view"].__class__.__name__,
                     exc_info=exc)
        return Response(
            {"detail": "The database is unavailable. Try again later."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    # Any other exception is a bug. Log it, and send a JSON 500 so that every
    # API error has the same {"detail": ...} shape.
    logger.error("Unhandled error in %s", context["view"].__class__.__name__,
                 exc_info=exc)
    return Response(
        {"detail": "Something went wrong on the server."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
