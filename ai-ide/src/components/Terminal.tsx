
import React, { useState, useEffect, useRef } from 'react';
import { Terminal as TerminalIcon } from 'lucide-react';

interface TerminalProps {
  logs: string[];
  onCommand: (cmd: string) => void;
}

export const Terminal: React.FC<TerminalProps> = ({ logs, onCommand }) => {
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    onCommand(input);
    setInput('');
  };

  const handleContainerClick = () => {
    inputRef.current?.focus();
  };

  return (
    <div 
      className="flex flex-col h-full bg-[#181818] text-slate-300 font-mono text-sm cursor-text"
      onClick={handleContainerClick}
    >
      <div className="flex items-center gap-2 px-4 py-2 bg-[#252526] text-xs uppercase tracking-wide border-b border-[#333] select-none cursor-default">
        <TerminalIcon className="w-3 h-3" />
        <span>Terminal</span>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-1 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
        {logs.map((log, index) => (
          <div key={index} className="whitespace-pre-wrap break-words font-mono leading-tight">
            {log.startsWith('>') ? (
              <span className="text-slate-500 font-bold">{log}</span>
            ) : log.startsWith('Error:') ? (
              <span className="text-red-400">{log}</span>
            ) : log.startsWith('Success:') ? (
              <span className="text-emerald-400">{log}</span>
            ) : (
              <span className="text-slate-300">{log}</span>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} className="flex items-center gap-2 p-2 border-t border-[#333] bg-[#1e1e1e]">
        <span className="text-blue-500 font-bold px-2 select-none">➜</span>
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a command (e.g., 'run')"
          className="flex-1 bg-transparent outline-none text-slate-200 placeholder-slate-600 font-mono"
          autoComplete="off"
          spellCheck="false"
        />
      </form>
    </div>
  );
};
