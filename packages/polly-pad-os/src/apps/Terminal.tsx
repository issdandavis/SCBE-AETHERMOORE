// @ts-nocheck
import React, { useState, useRef, useEffect } from 'react';
import { FS } from '@/utils/fs';

interface TerminalLine {
  type: 'input' | 'output' | 'error';
  content: string;
  prompt?: string;
}

const COMMANDS: Record<string, (...args: any[]) => { output: string; newCwd?: string }> = {
  help: () => ({
    output:
      'Available commands:\n  ls, cd, pwd, cat, echo, mkdir, rm, touch, clear, help, whoami, uname, date, calc, uptime, df, ps, find, grep, wc, history, reboot, fortune',
  }),
  ls: (args, cwd) => {
    const children = FS.getChildren(cwd);
    if (children.length === 0) return { output: 'total 0' };
    return {
      output: children
        .map(
          (c) =>
            `${c.type === 'directory' ? 'd' : '-'}rwxrwxrwx 1 user user ${(c.size || 0).toString().padStart(6)} ${new Date(c.modifiedAt).toLocaleDateString('en', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' })} ${c.name}`
        )
        .join('\n'),
    };
  },
  cd: (args, cwd) => {
    if (!args[0] || args[0] === '~') return { output: '', newCwd: 'user' };
    if (args[0] === '..') {
      const node = FS.getNode(cwd);
      if (node?.parentId) return { output: '', newCwd: node.parentId };
      return { output: '' };
    }
    if (args[0] === '/') return { output: '', newCwd: 'root' };
    const children = FS.getChildren(cwd);
    const target = children.find((c) => c.name === args[0] && c.type === 'directory');
    if (target) return { output: '', newCwd: target.id };
    return { output: `cd: no such file or directory: ${args[0]}` };
  },
  pwd: (args, cwd) => ({ output: FS.getPath(cwd) || '/' }),
  cat: (args, cwd) => {
    if (!args[0]) return { output: 'cat: missing file argument' };
    const children = FS.getChildren(cwd);
    const file = children.find((c) => c.name === args[0] && c.type === 'file');
    if (!file) return { output: `cat: ${args[0]}: No such file` };
    return { output: file.content || '(empty)' };
  },
  echo: (args) => ({ output: args.join(' ') }),
  mkdir: (args, cwd) => {
    if (!args[0]) return { output: 'mkdir: missing directory name' };
    if (FS.exists(cwd, args[0]))
      return { output: `mkdir: cannot create directory '${args[0]}': File exists` };
    FS.create(cwd, args[0], 'directory');
    return { output: '' };
  },
  touch: (args, cwd) => {
    if (!args[0]) return { output: 'touch: missing file argument' };
    FS.create(cwd, args[0], 'file');
    return { output: '' };
  },
  rm: (args, cwd) => {
    if (!args[0]) return { output: 'rm: missing file argument' };
    if (args[0] === '-rf' && args[1]) {
      const children = FS.getChildren(cwd);
      const target = children.find((c) => c.name === args[1]);
      if (target) {
        FS.delete(target.id);
        return { output: '' };
      }
    }
    const children = FS.getChildren(cwd);
    const target = children.find((c) => c.name === args[0]);
    if (target) {
      FS.delete(target.id);
      return { output: '' };
    }
    return { output: `rm: cannot remove '${args[0]}': No such file` };
  },
  clear: () => ({ output: '__CLEAR__' }),
  whoami: () => ({ output: 'user' }),
  uname: (args) => {
    if (args[0] === '-a')
      return { output: 'LinuxOS Web linuxos 5.15.0-generic #1 SMP x86_64 GNU/Linux' };
    return { output: 'LinuxOS' };
  },
  date: () => ({ output: new Date().toString() }),
  calc: (args) => {
    try {
      const expr = args.join(' ');
      // eslint-disable-next-line no-new-func
      const result = new Function('return ' + expr)();
      return { output: String(result) };
    } catch {
      return { output: 'calc: invalid expression' };
    }
  },
  uptime: () => {
    const s = Math.floor(performance.now() / 1000);
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    return {
      output: `${h}:${m.toString().padStart(2, '0')} up ${h}h ${m}m, 1 user, load average: 0.12, 0.08, 0.05`,
    };
  },
  df: () => ({
    output:
      'Filesystem     1K-blocks    Used Available Use% Mounted on\n/dev/sda1       97656372 12456372  85200000  13% /',
  }),
  ps: () => ({
    output:
      '  PID TTY          TIME CMD\n    1 ?        00:00:01 init\n  234 ?        00:00:03 desktop\n  567 ?        00:00:01 terminal\n  890 ?        00:00:00 browser',
  }),
  find: (args, cwd) => {
    const name = args.find((_, i) => args[i - 1] === '-name');
    const children = FS.getChildren(cwd);
    const matches = name ? children.filter((c) => c.name.includes(name)) : children;
    return { output: matches.map((c) => c.name).join('\n') || 'No matches found' };
  },
  grep: (args) => {
    if (args.length < 2) return { output: 'Usage: grep <pattern> <text>' };
    const [pattern, ...textParts] = args;
    const text = textParts.join(' ');
    return { output: text.includes(pattern) ? text : 'No match' };
  },
  wc: (args, cwd) => {
    if (!args[0]) return { output: '0 0 0' };
    const children = FS.getChildren(cwd);
    const file = children.find((c) => c.name === args[0] && c.type === 'file');
    if (!file) return { output: `wc: ${args[0]}: No such file` };
    const content = file.content || '';
    const lines = content.split('\n').length;
    const words = content.split(/\s+/).filter(Boolean).length;
    const chars = content.length;
    return { output: `${lines} ${words} ${chars} ${args[0]}` };
  },
  history: (args, _, history: string[]) => ({
    output: history.map((h, i) => `${(i + 1).toString().padStart(4)}  ${h}`).join('\n'),
  }),
  reboot: () => ({ output: 'System is going down for reboot now!' }),
  fortune: () => {
    const fortunes = [
      'The early bird gets the worm, but the second mouse gets the cheese.',
      'A journey of a thousand miles begins with a single step.',
      'To be or not to be, that is the question.',
      'The only way to do great work is to love what you do.',
      'Stay hungry, stay foolish.',
      'The best way to predict the future is to create it.',
      'Simplicity is the ultimate sophistication.',
    ];
    return { output: fortunes[Math.floor(Math.random() * fortunes.length)] };
  },
};

export default function Terminal({ windowId }: { windowId: string }) {
  const [lines, setLines] = useState<TerminalLine[]>([
    { type: 'output', content: 'LinuxOS Web Terminal - Type "help" for available commands' },
  ]);
  const [currentInput, setCurrentInput] = useState('');
  const [cwd, setCwd] = useState('user');
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [lines]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const executeCommand = (input: string) => {
    const trimmed = input.trim();
    if (!trimmed) {
      setLines((prev) => [...prev, { type: 'input', content: '', prompt: getPrompt() }]);
      return;
    }

    setHistory((prev) => [...prev, trimmed]);
    setHistoryIndex(-1);

    const parts = trimmed.split(/\s+/);
    const cmd = parts[0];
    const args = parts.slice(1);

    const handler = COMMANDS[cmd];
    let output: string;

    if (cmd === 'clear') {
      setLines([]);
      return;
    } else if (cmd === 'history') {
      output = COMMANDS.history(args, cwd, history).output;
    } else if (handler) {
      const result = handler(args, cwd);
      output = result.output;
      if (result.newCwd) setCwd(result.newCwd);
    } else {
      output = `${cmd}: command not found`;
    }

    const newLines: TerminalLine[] = [{ type: 'input', content: trimmed, prompt: getPrompt() }];
    if (output) newLines.push({ type: 'output', content: output });
    setLines((prev) => [...prev, ...newLines]);
  };

  const getPrompt = () => {
    const path = FS.getPath(cwd);
    return `user@linuxos:${path === '/home/user' ? '~' : path}$`;
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      executeCommand(currentInput);
      setCurrentInput('');
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (historyIndex < history.length - 1) {
        const newIndex = historyIndex + 1;
        setHistoryIndex(newIndex);
        setCurrentInput(history[history.length - 1 - newIndex] || '');
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1;
        setHistoryIndex(newIndex);
        setCurrentInput(history[history.length - 1 - newIndex] || '');
      } else {
        setHistoryIndex(-1);
        setCurrentInput('');
      }
    }
  };

  return (
    <div
      className="w-full h-full bg-[#0b1120] text-green-400 font-mono text-xs flex flex-col overflow-hidden"
      onClick={() => inputRef.current?.focus()}
    >
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3">
        {lines.map((line, i) => (
          <div key={i} className="whitespace-pre-wrap break-all">
            {line.type === 'input' && (
              <span className="text-blue-400">{line.prompt || getPrompt()} </span>
            )}
            <span
              className={
                line.type === 'error'
                  ? 'text-red-400'
                  : line.type === 'input'
                    ? 'text-green-300'
                    : 'text-green-400/80'
              }
            >
              {line.content}
            </span>
          </div>
        ))}
        <div className="flex items-center">
          <span className="text-blue-400">{getPrompt()} </span>
          <input
            ref={inputRef}
            type="text"
            value={currentInput}
            onChange={(e) => setCurrentInput(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1 bg-transparent outline-none text-green-300 caret-green-400"
            spellCheck={false}
            autoComplete="off"
          />
        </div>
      </div>
    </div>
  );
}
