import { useCallback, useEffect, useRef, useState } from 'react';

import { createTodo, fetchTodos } from '../api/todos';

// Holds the TODO list state and the actions that change it. Components get
// plain values and callbacks, and do not know about HTTP.
export function useTodos() {
  const [todos, setTodos] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  // The in-flight list request. A new refresh cancels the old one, so a slow
  // old response cannot overwrite a newer list.
  const controllerRef = useRef(null);

  const refresh = useCallback(async () => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    setIsLoading(true);
    try {
      const latest = await fetchTodos({ signal: controller.signal });
      if (controller.signal.aborted) return;
      setTodos(latest);
      setError(null);
    } catch (err) {
      if (controller.signal.aborted) return;
      setError(err.message);
    } finally {
      // An aborted request belongs to an unmounted component or to an older
      // refresh. Neither may change the state.
      if (!controller.signal.aborted) setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    // On unmount, cancel the request so that it does not set state later.
    return () => controllerRef.current?.abort();
  }, [refresh]);

  // Create errors go to the caller (the form shows them). After a successful
  // create, load the list again from the server, which is the source of truth.
  // `refresh` never throws: if the reload fails, the error shows in the list
  // area, and addTodo still resolves, because the TODO was saved.
  const addTodo = useCallback(
    async (description) => {
      await createTodo(description);
      await refresh();
    },
    [refresh]
  );

  return { todos, isLoading, error, addTodo };
}
