import './App.css';
import { TodoForm } from './components/TodoForm';
import { TodoList } from './components/TodoList';
import { useTodos } from './hooks/useTodos';

export function App() {
  const { todos, isLoading, error, addTodo } = useTodos();

  return (
    <main className="App">
      <TodoList todos={todos} isLoading={isLoading} error={error} />
      <TodoForm onCreate={addTodo} />
    </main>
  );
}

export default App;
