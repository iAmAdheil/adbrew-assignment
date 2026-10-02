import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import App from './App';
import { API_BASE_URL } from './api/todos';

const TODOS_URL = `${API_BASE_URL}/todos/`;

function jsonResponse(body, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  });
}

const milk = { id: '1', description: 'Buy milk', created_at: '2026-10-02T06:00:00+00:00' };
const bread = { id: '2', description: 'Buy bread', created_at: '2026-10-02T06:01:00+00:00' };

// jsdom has no fetch, so jest.spyOn cannot wrap it. Install a mock and put
// back whatever was there before.
const originalFetch = window.fetch;

beforeEach(() => {
  window.fetch = jest.fn();
});

afterEach(() => {
  window.fetch = originalFetch;
});

test('shows the TODOs from the API', async () => {
  window.fetch.mockReturnValueOnce(jsonResponse({ todos: [milk] }));

  render(<App />);

  expect(await screen.findByText('Buy milk')).toBeInTheDocument();
  expect(window.fetch).toHaveBeenCalledWith(
    TODOS_URL,
    expect.objectContaining({ signal: expect.anything() })
  );
});

test('shows an empty state when there are no TODOs', async () => {
  window.fetch.mockReturnValueOnce(jsonResponse({ todos: [] }));

  render(<App />);

  expect(await screen.findByText('No TODOs yet.')).toBeInTheDocument();
});

test('shows the API error message when the list cannot load', async () => {
  window.fetch.mockReturnValueOnce(
    jsonResponse({ detail: 'The database is unavailable. Try again later.' }, 503)
  );

  render(<App />);

  expect(await screen.findByRole('alert')).toHaveTextContent(
    'The database is unavailable. Try again later.'
  );
});

test('creates a TODO, then loads the list again', async () => {
  window.fetch
    .mockReturnValueOnce(jsonResponse({ todos: [milk] }))
    .mockReturnValueOnce(jsonResponse({ todo: bread }, 201))
    .mockReturnValueOnce(jsonResponse({ todos: [bread, milk] }));

  render(<App />);
  await screen.findByText('Buy milk');

  userEvent.type(screen.getByLabelText('ToDo:'), '  Buy bread  ');
  userEvent.click(screen.getByRole('button', { name: 'Add ToDo!' }));

  expect(await screen.findByText('Buy bread')).toBeInTheDocument();
  expect(window.fetch).toHaveBeenNthCalledWith(
    2,
    TODOS_URL,
    expect.objectContaining({ method: 'POST', body: JSON.stringify({ description: 'Buy bread' }) })
  );
  expect(window.fetch).toHaveBeenCalledTimes(3);
  await waitFor(() => expect(screen.getByLabelText('ToDo:')).toHaveValue(''));
});

test('does not call the API for an empty description', async () => {
  window.fetch.mockReturnValueOnce(jsonResponse({ todos: [] }));

  render(<App />);
  await screen.findByText('No TODOs yet.');

  userEvent.type(screen.getByLabelText('ToDo:'), '   ');
  userEvent.click(screen.getByRole('button', { name: 'Add ToDo!' }));

  expect(await screen.findByRole('alert')).toHaveTextContent('Enter a description.');
  expect(window.fetch).toHaveBeenCalledTimes(1);
});

test('keeps the text and shows the error when the create fails', async () => {
  window.fetch
    .mockReturnValueOnce(jsonResponse({ todos: [] }))
    .mockReturnValueOnce(
      jsonResponse({ detail: 'The description must be at most 500 characters.' }, 400)
    );

  render(<App />);
  await screen.findByText('No TODOs yet.');

  userEvent.type(screen.getByLabelText('ToDo:'), 'Buy eggs');
  userEvent.click(screen.getByRole('button', { name: 'Add ToDo!' }));

  expect(await screen.findByRole('alert')).toHaveTextContent(
    'The description must be at most 500 characters.'
  );
  expect(screen.getByLabelText('ToDo:')).toHaveValue('Buy eggs');
});

test('shows a network error when the server cannot be reached', async () => {
  window.fetch.mockReturnValueOnce(Promise.reject(new TypeError('Failed to fetch')));

  render(<App />);

  expect(await screen.findByRole('alert')).toHaveTextContent('Could not reach the server.');
});

test('clears the form when the create succeeds but the reload fails', async () => {
  window.fetch
    .mockReturnValueOnce(jsonResponse({ todos: [] }))
    .mockReturnValueOnce(jsonResponse({ todo: bread }, 201))
    .mockReturnValueOnce(
      jsonResponse({ detail: 'The database is unavailable. Try again later.' }, 503)
    );

  render(<App />);
  await screen.findByText('No TODOs yet.');

  userEvent.type(screen.getByLabelText('ToDo:'), 'Buy bread');
  userEvent.click(screen.getByRole('button', { name: 'Add ToDo!' }));

  // The TODO was saved, so the form clears. The reload error shows in the list area.
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Could not load TODOs: The database is unavailable.'
  );
  await waitFor(() => expect(screen.getByLabelText('ToDo:')).toHaveValue(''));
});

test('shows a clear error when the server sends an unexpected response', async () => {
  window.fetch.mockReturnValueOnce(jsonResponse({ items: [] }));

  render(<App />);

  expect(await screen.findByRole('alert')).toHaveTextContent(
    'The server sent an unexpected response.'
  );
});
