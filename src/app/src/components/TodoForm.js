import { useEffect, useRef, useState } from 'react';

import { DESCRIPTION_MAX_LENGTH } from '../constants';

// `onCreate(description)` returns a promise. It rejects with an Error whose
// message is safe to show to the user.
export function TodoForm({ onCreate }) {
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  // onCreate is async. If the form unmounts before it settles, the form must
  // not set state any more.
  const isMountedRef = useRef(true);
  useEffect(() => () => {
    isMountedRef.current = false;
  }, []);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const trimmed = description.trim();
    if (!trimmed) {
      setError('Enter a description.');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await onCreate(trimmed);
      if (isMountedRef.current) setDescription('');
    } catch (err) {
      // Keep the text in the input so that the user can try again.
      if (isMountedRef.current) setError(err.message);
    } finally {
      if (isMountedRef.current) setIsSubmitting(false);
    }
  };

  return (
    <section aria-labelledby="todo-form-heading">
      <h1 id="todo-form-heading">Create a ToDo</h1>
      <form onSubmit={handleSubmit} noValidate>
        <div>
          <label htmlFor="todo-description">ToDo: </label>
          <input
            id="todo-description"
            type="text"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            maxLength={DESCRIPTION_MAX_LENGTH}
            aria-invalid={Boolean(error)}
            aria-describedby={error ? 'todo-form-error' : undefined}
          />
        </div>
        <div className="form-actions">
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Adding…' : 'Add ToDo!'}
          </button>
        </div>
        {error && (
          <p id="todo-form-error" role="alert" className="error">
            {error}
          </p>
        )}
      </form>
    </section>
  );
}
