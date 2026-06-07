import React, { useState, useEffect } from 'react';
import { Bell, Plus, Trash2, Check, Clock, Download, Upload } from 'lucide-react';

interface Reminder {
  id: string;
  text: string;
  datetime: string;
  done: boolean;
  created: number;
}
const STORAGE_KEY = 'linuxos_reminders';

export default function Reminders() {
  const [reminders, setReminders] = useState<Reminder[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch {
      /* ignore */
    }
    return [
      {
        id: '1',
        text: 'Try the Snake game',
        datetime: new Date().toISOString().slice(0, 16),
        done: false,
        created: Date.now(),
      },
      {
        id: '2',
        text: 'Explore Settings',
        datetime: new Date().toISOString().slice(0, 16),
        done: false,
        created: Date.now(),
      },
      {
        id: '3',
        text: 'Read the Wiki',
        datetime: new Date(Date.now() + 86400000).toISOString().slice(0, 16),
        done: true,
        created: Date.now(),
      },
    ];
  });
  const [showAdd, setShowAdd] = useState(false);
  const [text, setText] = useState('');
  const [datetime, setDatetime] = useState(new Date().toISOString().slice(0, 16));
  const [filter, setFilter] = useState<'all' | 'active' | 'done' | 'overdue'>('all');

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(reminders));
  }, [reminders]);

  const now = new Date();
  const isOverdue = (dt: string) => new Date(dt) < now;

  const add = () => {
    if (!text.trim()) return;
    setReminders([
      ...reminders,
      { id: Date.now().toString(), text: text.trim(), datetime, done: false, created: Date.now() },
    ]);
    setText('');
    setDatetime(new Date().toISOString().slice(0, 16));
    setShowAdd(false);
  };

  const toggle = (id: string) =>
    setReminders((prev) => prev.map((r) => (r.id === id ? { ...r, done: !r.done } : r)));
  const remove = (id: string) => setReminders((prev) => prev.filter((r) => r.id !== id));

  const exportReminders = () => {
    const blob = new Blob([JSON.stringify(reminders, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `reminders-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const importReminders = () => {
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
          if (Array.isArray(imported)) setReminders((prev) => [...imported, ...prev]);
        } catch {
          /* ignore */
        }
      };
      reader.readAsText(file);
    };
    input.click();
  };

  const filtered = reminders
    .filter((r) => {
      if (filter === 'active') return !r.done;
      if (filter === 'done') return r.done;
      if (filter === 'overdue') return !r.done && isOverdue(r.datetime);
      return true;
    })
    .sort((a, b) => new Date(a.datetime).getTime() - new Date(b.datetime).getTime());

  const stats = {
    total: reminders.length,
    done: reminders.filter((r) => r.done).length,
    overdue: reminders.filter((r) => !r.done && isOverdue(r.datetime)).length,
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg text-blue-200 font-semibold flex items-center gap-2">
          <Bell size={18} className="text-yellow-400" />
          Reminders
        </h2>
        <div className="flex gap-1">
          <button
            onClick={importReminders}
            className="p-1.5 rounded hover:bg-blue-500/20 text-blue-400 transition-colors"
            title="Import"
          >
            <Upload size={14} />
          </button>
          <button
            onClick={exportReminders}
            className="p-1.5 rounded hover:bg-blue-500/20 text-blue-400 transition-colors"
            title="Export"
          >
            <Download size={14} />
          </button>
          <button
            onClick={() => setShowAdd(!showAdd)}
            className="p-1.5 rounded hover:bg-blue-500/20 text-blue-400"
          >
            <Plus size={16} />
          </button>
        </div>
      </div>

      <div className="flex gap-1 mb-3">
        <div className="text-[10px] px-2 py-1 rounded bg-blue-500/10 text-blue-300/50">
          {stats.total} total
        </div>
        <div className="text-[10px] px-2 py-1 rounded bg-green-500/10 text-green-300/50">
          {stats.done} done
        </div>
        {stats.overdue > 0 && (
          <div className="text-[10px] px-2 py-1 rounded bg-red-500/10 text-red-300/50">
            {stats.overdue} overdue
          </div>
        )}
        <div className="flex-1" />
        {(['all', 'active', 'done', 'overdue'] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-2 py-1 rounded-lg text-[10px] transition-colors ${filter === f ? 'bg-blue-500/20 text-blue-200' : 'text-blue-300/30 hover:text-blue-200/60'}`}
          >
            {f}
          </button>
        ))}
      </div>

      {showAdd && (
        <div className="flex flex-col gap-2 mb-3">
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && add()}
            placeholder="New reminder..."
            className="bg-[#162032] border border-blue-500/15 rounded-lg px-3 py-1.5 text-xs outline-none focus:border-blue-500/30"
            autoFocus
          />
          <div className="flex gap-2">
            <input
              type="datetime-local"
              value={datetime}
              onChange={(e) => setDatetime(e.target.value)}
              className="flex-1 bg-[#162032] border border-blue-500/15 rounded-lg px-2 py-1 text-xs outline-none focus:border-blue-500/30"
            />
            <button
              onClick={add}
              className="px-3 py-1.5 rounded-lg bg-blue-500/20 text-blue-200 text-xs hover:bg-blue-500/30"
            >
              Add
            </button>
          </div>
        </div>
      )}

      <div className="space-y-1.5 flex-1 overflow-y-auto">
        {filtered.map((r) => (
          <div
            key={r.id}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-xl bg-[#162032] border transition-all group ${!r.done && isOverdue(r.datetime) ? 'border-red-500/20' : 'border-blue-500/5'}`}
          >
            <button
              onClick={() => toggle(r.id)}
              className={`transition-colors ${r.done ? 'text-green-400' : 'text-blue-300/30 hover:text-blue-400'}`}
            >
              {r.done ? <Check size={16} /> : <Bell size={16} />}
            </button>
            <div className="flex-1 min-w-0">
              <div
                className={`text-xs ${r.done ? 'line-through text-blue-300/30' : 'text-blue-200/70'}`}
              >
                {r.text}
              </div>
              <div className="flex items-center gap-1 text-[10px]">
                <Clock
                  size={8}
                  className={
                    isOverdue(r.datetime) && !r.done ? 'text-red-400/50' : 'text-blue-400/20'
                  }
                />
                <span
                  className={
                    isOverdue(r.datetime) && !r.done ? 'text-red-400/50' : 'text-blue-300/20'
                  }
                >
                  {new Date(r.datetime).toLocaleString([], {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                  {isOverdue(r.datetime) && !r.done && ' (overdue)'}
                </span>
              </div>
            </div>
            <button
              onClick={() => remove(r.id)}
              className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/20 text-blue-300/20 hover:text-red-400 transition-all"
            >
              <Trash2 size={12} />
            </button>
          </div>
        ))}
        {filtered.length === 0 && (
          <div className="text-center text-xs text-blue-400/20 py-8">No reminders</div>
        )}
      </div>
    </div>
  );
}
