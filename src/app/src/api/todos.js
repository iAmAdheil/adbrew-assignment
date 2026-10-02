// HTTP client for the TODO API. Components and hooks call these functions
// and never call fetch() directly.

// The browser runs on the host, not inside Docker, so it reaches the API
// through the published port on localhost.
export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status; // 0 means the request did not reach the server.
  }
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: { Accept: 'application/json', ...options.headers },
    });
  } catch (error) {
    // The caller cancelled the request. Let the caller ignore it.
    if (error.name === 'AbortError') throw error;
    throw new ApiError('Could not reach the server. Try again later.', 0);
  }

  // An error page (for example a Django 500 in HTML) is not JSON.
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const message = body?.detail || `Request failed with status ${response.status}.`;
    throw new ApiError(message, response.status);
  }
  return body;
}

// A 2xx response with an unexpected body is a server bug. Report it as an
// ApiError, so that the UI shows a clear message and not a TypeError.
function unexpectedResponse() {
  return new ApiError('The server sent an unexpected response.', 200);
}

export async function fetchTodos({ signal } = {}) {
  const body = await request('/todos/', { signal });
  if (!Array.isArray(body?.todos)) throw unexpectedResponse();
  return body.todos;
}

export async function createTodo(description) {
  const body = await request('/todos/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ description }),
  });
  if (!body?.todo) throw unexpectedResponse();
  return body.todo;
}
