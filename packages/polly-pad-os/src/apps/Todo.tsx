import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Check, Circle, Calendar, Search, Download, Upload } from 'lucide-react';

interface Todo {
  id: string;
  text: string;
  done: boolean;
  priority: 'low' | 'medium' | 'high';
  created: number;
  tags: string[];
}
const STORAGE_KEY = 'linuxos_todos';

export default function TodoApp() {
  const [todos, setTodos] = useState<Todo[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch {
      /* ignore */
    }
    return [
      {
        id: '1',
        text: 'Explore the desktop',
        done: true,
        priority: 'low',
        created: Date.now(),
        tags: ['setup'],
      },
      {
        id: '2',
        text: 'Try some games',
        done: false,
        priority: 'medium',
        created: Date.now(),
        tags: ['fun'],
      },
      {
        id: '3',
        text: 'Customize settings',
        done: false,
        priority: 'high',
        created: Date.now(),
        tags: ['setup'],
      },
    ];
  });
  const [input, setInput] = useState('');
  const [filter, setFilter] = useState<'all' | 'active' | 'done'>('all');
  const [priorityFilter, setPriorityFilter] = useState<'all' | 'low' | 'medium' | 'high'>('all');
  const [search, setSearch] = useState('');

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(todos));
  }, [todos]);

  const addTodo = () => {
    if (!input.trim()) return;
    const tags = input.match(/#(\w+)/g)?.map((t) => t.slice(1)) || [];
    const text = input.replace(/#\w+/g, '').trim();
    setTodos([
      ...todos,
      {
        id: Date.now().toString(),
        text,
        done: false,
        priority: 'medium',
        created: Date.now(),
        tags,
      },
    ]);
    setInput('');
  };

  const toggle = (id: string) =>
    setTodos(todos.map((t) => (t.id === id ? { ...t, done: !t.done } : t)));
  const remove = (id: string) => setTodos(todos.filter((t) => t.id !== id));
  const setPriority = (id: string, priority: 'low' | 'medium' | 'high') =>
    setTodos(todos.map((t) => (t.id === id ? { ...t, priority } : t)));

  const exportTodos = () => {
    const blob = new Blob([JSON.stringify(todos, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `todos-export-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const importTodos = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (ev) => {
        try {
          const imported = JSON.parse(ev.target?.result as string);
          if (Array.isArray(imported)) setTodos((prev) => [...imported, ...prev]);
        } catch {
          /* ignore */
        }
      };
      reader.readAsText(file);
    };
    input.click();
  };

  const filtered = todos
    .filter((t) => (filter === 'all' ? true : filter === 'done' ? t.done : !t.done))
    .filter((t) => (priorityFilter === 'all' ? true : t.priority === priorityFilter))
    .filter(
      (t) =>
        t.text.toLowerCase().includes(search.toLowerCase()) ||
        t.tags.some((tag) => tag.toLowerCase().includes(search.toLowerCase()))
    );

  const priorityColors = {
    low: 'bg-blue-500/20 text-blue-300',
    medium: 'bg-yellow-500/20 text-yellow-300',
    high: 'bg-red-500/20 text-red-300',
  };
  const stats = {
    total: todos.length,
    done: todos.filter((t) => t.done).length,
    high: todos.filter((t) => t.priority === 'high' && !t.done).length,
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 p-4">
      <h2 className="text-lg text-blue-200 font-semibold mb-3 flex items-center gap-2">
        <Calendar size={18} className="text-blue-400" />
        Todo List
      </h2>
      <div className="flex gap-2 mb-2">
        <div className="text-[10px] px-2 py-1 rounded bg-blue-500/10 text-blue-300/50">
          {stats.total} total
        </div>
        <div className="text-[10px] px-2 py-1 rounded bg-green-500/10 text-green-300/50">
          {stats.done} done
        </div>
        {stats.high > 0 && (
          <div className="text-[10px] px-2 py-1 rounded bg-red-500/10 text-red-300/50">
            {stats.high} urgent
          </div>
        )}
        <div className="flex-1" />
        <button
          onClick={importTodos}
          className="p-1 rounded hover:bg-blue-500/20 text-blue-400 transition-colors"
          title="Import"
        >
          <Upload size={12} />
        </button>
        <button
          onClick={exportTodos}
          className="p-1 rounded hover:bg-blue-500/20 text-blue-400 transition-colors"
          title="Export"
        >
          <Download size={12} />
        </button>
      </div>
      <div className="flex gap-2 mb-2">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search..."
          className="flex-1 bg-[#162032] border border-blue-500/15 rounded-lg px-3 py-1.5 text-xs outline-none focus:border-blue-500/30"
        />
      </div>
      <div className="flex gap-2 mb-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && addTodo()}
          placeholder="Add a task... Use #tag"
          className="flex-1 bg-[#162032] border border-blue-500/15 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/30"
        />
        <button
          onClick={addTodo}
          className="p-2 rounded-lg bg-blue-500/20 hover:bg-blue-500/30 text-blue-200 transition-colors"
        >
          <Plus size={18} />
        </button>
      </div>
      <div className="flex gap-1 mb-3">
        {(['all', 'active', 'done'] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1 rounded-lg text-xs transition-colors ${filter === f ? 'bg-blue-500/20 text-blue-200' : 'text-blue-300/40 hover:text-blue-200/60'}`}
          >
            {f}
          </button>
        ))}
        <div className="w-px h-4 bg-blue-500/10 mx-1 self-center" />
        {(['all', 'low', 'medium', 'high'] as const).map((p) => (
          <button
            key={p}
            onClick={() => setPriorityFilter(p)}
            className={`px-2 py-1 rounded-lg text-[10px] transition-colors ${priorityFilter === p ? (p === 'all' ? 'bg-blue-500/20 text-blue-200' : priorityColors[p]) : 'text-blue-300/30 hover:text-blue-200/50'}`}
          >
            {p === 'all' ? 'All' : p[0].toUpperCase()}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto space-y-1.5">
        {filtered.map((todo) => (
          <div
            key={todo.id}
            className="flex items-center gap-3 px-3 py-2 rounded-xl bg-[#162032] border border-blue-500/5 group"
          >
            <button
              onClick={() => toggle(todo.id)}
              className={`transition-colors ${todo.done ? 'text-green-400' : 'text-blue-300/30 hover:text-blue-400'}`}
            >
              {todo.done ? <Check size={16} /> : <Circle size={16} />}
            </button>
            <span
              className={`flex-1 text-sm ${todo.done ? 'line-through text-blue-300/30' : 'text-blue-200/70'}`}
            >
              {todo.text}
            </span>
            {todo.tags.map((tag) => (
              <span
                key={tag}
                className="text-[9px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-300/40"
              >
                #{tag}
              </span>
            ))}
            <select
              value={todo.priority}
              onChange={(e) => setPriority(todo.id, e.target.value as any)}
              className={`text-[9px] px-1.5 py-0.5 rounded border-none outline-none cursor-pointer ${priorityColors[todo.priority as keyof typeof priorityColors]}`}
            >
              <option value="low">Low</option>
              <option value="medium">Med</option>
              <option value="high">High</option>
            </select>
            <button
              onClick={() => remove(todo.id)}
              className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/20 text-blue-300/30 hover:text-red-400 transition-all"
            >
              <Trash2 size={13} />
            </button>
          </div>
        ))}
        {filtered.length === 0 && (
          <p className="text-center text-sm text-blue-300/20 py-8">No tasks</p>
        )}
      </div>
      <div className="text-xs text-blue-300/30 mt-2">
        {todos.filter((t) => !t.done).length} remaining
      </div>
    </div>
  );
}
