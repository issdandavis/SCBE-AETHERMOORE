import React, { useState, useEffect } from 'react';
import { Plus, Trash2, FileText, Search, Download, Upload } from 'lucide-react';

interface Note {
  id: string;
  title: string;
  content: string;
  color: string;
  updated: number;
}
const COLORS = [
  'bg-[#162032]',
  'bg-blue-500/10',
  'bg-green-500/10',
  'bg-yellow-500/10',
  'bg-purple-500/10',
  'bg-pink-500/10',
];
const STORAGE_KEY = 'linuxos_notes';

export default function Notes() {
  const [notes, setNotes] = useState<Note[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch {
      /* ignore */
    }
    return [
      {
        id: '1',
        title: 'Welcome',
        content:
          'Click + to create a new note. Click a note to edit it. All notes are saved automatically.',
        color: COLORS[0],
        updated: Date.now(),
      },
      {
        id: '2',
        title: 'Ideas',
        content: '- Build a web app\n- Learn Rust\n- Explore AI\n- Read about SCBE framework',
        color: COLORS[1],
        updated: Date.now() - 3600000,
      },
    ];
  });
  const [selected, setSelected] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(notes));
  }, [notes]);

  const addNote = () => {
    const note: Note = {
      id: Date.now().toString(),
      title: 'New Note',
      content: '',
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
      updated: Date.now(),
    };
    setNotes([note, ...notes]);
    setSelected(note.id);
  };

  const updateNote = (id: string, updates: Partial<Note>) =>
    setNotes((prev) =>
      prev.map((n) => (n.id === id ? { ...n, ...updates, updated: Date.now() } : n))
    );

  const deleteNote = (id: string) => {
    setNotes((prev) => prev.filter((n) => n.id !== id));
    if (selected === id) setSelected(null);
  };

  const exportNotes = () => {
    const data = JSON.stringify(notes, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `notes-export-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const importNotes = () => {
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
          if (Array.isArray(imported)) {
            setNotes((prev) => [...imported, ...prev]);
          }
        } catch {
          /* ignore */
        }
      };
      reader.readAsText(file);
    };
    input.click();
  };

  const activeNote = notes.find((n) => n.id === selected);

  const filtered = notes.filter(
    (n) =>
      n.title.toLowerCase().includes(search.toLowerCase()) ||
      n.content.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="w-full h-full flex bg-[#0d1926] text-blue-100/80">
      <div className="w-52 border-r border-blue-500/10 flex flex-col">
        <div className="flex items-center justify-between p-3 border-b border-blue-500/10">
          <h2 className="text-sm text-blue-200 font-semibold">Notes</h2>
          <div className="flex gap-1">
            <button
              onClick={importNotes}
              className="p-1 rounded hover:bg-blue-500/20 text-blue-400 transition-colors"
              title="Import"
            >
              <Upload size={14} />
            </button>
            <button
              onClick={exportNotes}
              className="p-1 rounded hover:bg-blue-500/20 text-blue-400 transition-colors"
              title="Export"
            >
              <Download size={14} />
            </button>
            <button
              onClick={addNote}
              className="p-1 rounded hover:bg-blue-500/20 text-blue-400 transition-colors"
            >
              <Plus size={16} />
            </button>
          </div>
        </div>
        <div className="p-2 border-b border-blue-500/10">
          <div className="relative">
            <Search
              size={12}
              className="absolute left-2 top-1/2 -translate-y-1/2 text-blue-400/30"
            />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search notes..."
              className="w-full bg-[#162032] border border-blue-500/15 rounded-lg pl-7 pr-2 py-1.5 text-xs outline-none focus:border-blue-500/30"
            />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {filtered.map((note) => (
            <button
              key={note.id}
              onClick={() => setSelected(note.id)}
              className={`w-full text-left px-3 py-2 transition-colors border-l-2 ${selected === note.id ? 'bg-blue-500/10 border-blue-500' : 'border-transparent hover:bg-blue-500/5'}`}
            >
              <div className="text-xs text-blue-200/70 truncate">{note.title || 'Untitled'}</div>
              <div className="text-[10px] text-blue-300/30 truncate">
                {note.content.slice(0, 50) || 'Empty'}
              </div>
              <div className="text-[9px] text-blue-400/20 mt-0.5">
                {new Date(note.updated).toLocaleDateString()}
              </div>
            </button>
          ))}
          {filtered.length === 0 && (
            <div className="p-4 text-xs text-blue-400/20 text-center">No notes found</div>
          )}
        </div>
      </div>
      {activeNote ? (
        <div className={`flex-1 flex flex-col p-4 ${activeNote.color}`}>
          <div className="flex items-center gap-2 mb-3">
            <input
              value={activeNote.title}
              onChange={(e) => updateNote(activeNote.id, { title: e.target.value })}
              className="flex-1 bg-transparent text-lg font-semibold outline-none text-blue-100 placeholder-blue-300/30"
              placeholder="Note title"
            />
            <button
              onClick={() => deleteNote(activeNote.id)}
              className="p-1.5 rounded hover:bg-red-500/20 text-blue-300/30 hover:text-red-400"
            >
              <Trash2 size={14} />
            </button>
          </div>
          <textarea
            value={activeNote.content}
            onChange={(e) => updateNote(activeNote.id, { content: e.target.value })}
            className="flex-1 bg-transparent outline-none text-sm text-blue-200/70 resize-none placeholder-blue-300/20 leading-relaxed"
            placeholder="Start typing..."
          />
          <div className="text-[10px] text-blue-400/20 mt-2">
            Last edited: {new Date(activeNote.updated).toLocaleString()}
          </div>
        </div>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center text-blue-400/20">
          <FileText size={48} />
          <p className="text-sm mt-2">Select a note or create one</p>
        </div>
      )}
    </div>
  );
}
