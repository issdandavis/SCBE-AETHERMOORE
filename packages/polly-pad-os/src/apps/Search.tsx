import React, { useState } from 'react';
import { useOS } from '@/os/OSStore';
import {
  Search as SearchIcon,
  FileText,
  Folder,
  Globe,
  Gamepad2,
  Settings,
  Calculator,
  Calendar,
  Clock,
  Music,
  Image,
  Code,
  Mail,
  CloudSun,
  BookOpen,
} from 'lucide-react';

const SEARCH_ITEMS = [
  { name: 'File Manager', id: 'files', icon: <Folder size={18} />, type: 'App' },
  { name: 'Terminal', id: 'terminal', icon: <Code size={18} />, type: 'App' },
  { name: 'Text Editor', id: 'texteditor', icon: <FileText size={18} />, type: 'App' },
  { name: 'Browser', id: 'browser', icon: <Globe size={18} />, type: 'App' },
  { name: 'Calculator', id: 'calculator', icon: <Calculator size={18} />, type: 'App' },
  { name: 'Settings', id: 'settings', icon: <Settings size={18} />, type: 'App' },
  { name: 'Calendar', id: 'calendar', icon: <Calendar size={18} />, type: 'App' },
  { name: 'Clock', id: 'clock', icon: <Clock size={18} />, type: 'App' },
  { name: 'Snake Game', id: 'snake', icon: <Gamepad2 size={18} />, type: 'Game' },
  { name: 'Tetris', id: 'tetris', icon: <Gamepad2 size={18} />, type: 'Game' },
  { name: 'Minesweeper', id: 'minesweeper', icon: <Gamepad2 size={18} />, type: 'Game' },
  { name: 'Music Player', id: 'musicplayer', icon: <Music size={18} />, type: 'Media' },
  { name: 'Photo Viewer', id: 'photoviewer', icon: <Image size={18} />, type: 'Media' },
  { name: 'Paint', id: 'drawing', icon: <Image size={18} />, type: 'Media' },
  { name: 'Notes', id: 'notes', icon: <FileText size={18} />, type: 'Productivity' },
  { name: 'Todo List', id: 'todo', icon: <FileText size={18} />, type: 'Productivity' },
  { name: 'Code Editor', id: 'codeeditor', icon: <Code size={18} />, type: 'Development' },
  { name: 'Mail', id: 'mail', icon: <Mail size={18} />, type: 'Internet' },
  { name: 'Weather', id: 'weather', icon: <CloudSun size={18} />, type: 'Utility' },
  { name: 'Browser', id: 'browser', icon: <Globe size={18} />, type: 'Internet' },
  { name: 'Terminal Commands', id: 'terminal', icon: <Code size={18} />, type: 'Help' },
  { name: 'System Settings', id: 'settings', icon: <Settings size={18} />, type: 'System' },
  { name: 'Documentation', id: 'wiki', icon: <BookOpen size={18} />, type: 'Help' },
];

export default function SearchApp() {
  const { openApp } = useOS();
  const [query, setQuery] = useState('');

  const results = query.trim()
    ? SEARCH_ITEMS.filter((item) => item.name.toLowerCase().includes(query.toLowerCase()))
    : [];

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 p-4">
      <div className="relative mb-4">
        <SearchIcon
          size={16}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-blue-400/40"
        />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search apps, files, settings..."
          className="w-full bg-[#162032] border border-blue-500/15 rounded-xl pl-9 pr-4 py-2.5 text-sm text-blue-100 placeholder-blue-400/30 outline-none focus:border-blue-500/40 transition-all"
          autoFocus
        />
      </div>

      {results.length === 0 && query.trim() && (
        <div className="flex-1 flex flex-col items-center justify-center text-blue-400/20">
          <SearchIcon size={40} />
          <p className="mt-2 text-sm">No results found</p>
        </div>
      )}

      {!query.trim() && (
        <div className="flex-1 flex flex-col items-center justify-center text-blue-400/20">
          <SearchIcon size={48} />
          <p className="mt-2 text-sm">Type to search across your system</p>
        </div>
      )}

      <div className="space-y-1">
        {results.map((item, i) => (
          <button
            key={`${item.id}-${i}`}
            onClick={() => openApp(item.id)}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-blue-500/10 transition-colors text-left group"
          >
            <div className="text-blue-400/50 group-hover:text-blue-300 transition-colors">
              {item.icon}
            </div>
            <div className="flex-1">
              <div className="text-sm text-blue-200/80 group-hover:text-blue-100">{item.name}</div>
              <div className="text-[10px] text-blue-400/30">{item.type}</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
