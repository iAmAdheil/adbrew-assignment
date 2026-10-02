export function TodoList({ todos, isLoading, error }) {
  return (
    <section aria-labelledby="todo-list-heading">
      <h1 id="todo-list-heading">List of TODOs</h1>
      {error && (
        <p role="alert" className="error">
          Could not load TODOs: {error}
        </p>
      )}
      <TodoListBody todos={todos} isLoading={isLoading} hasError={Boolean(error)} />
    </section>
  );
}

function TodoListBody({ todos, isLoading, hasError }) {
  // Keep the current list on screen while a refresh runs.
  if (isLoading && todos.length === 0) return <p>Loading…</p>;
  if (todos.length === 0) return hasError ? null : <p>No TODOs yet.</p>;
  return (
    <ul className="todo-list">
      {todos.map((todo) => (
        <li key={todo.id}>{todo.description}</li>
      ))}
    </ul>
  );
}
