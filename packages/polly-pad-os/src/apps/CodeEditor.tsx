import React, { useState, useCallback } from 'react';
import { FileText, Play, Copy, Trash2, Clock, AlertCircle, CheckCircle } from 'lucide-react';

interface LogEntry {
  type: 'log' | 'error' | 'warn' | 'info' | 'table' | 'time';
  message: string;
  timestamp: number;
}

export default function CodeEditor() {
  const [code, setCode] = useState(
    `// Welcome to Code Editor\n// Try: console.log(), console.error(), console.warn(), console.table(), console.time()\n\nfunction fibonacci(n) {\n  if (n <= 1) return n;\n  return fibonacci(n - 1) + fibonacci(n - 2);\n}\n\nconsole.time('fib');\nconsole.log('Fibonacci(10):', fibonacci(10));\nconsole.timeEnd('fib');\n\nconsole.table([\n  { name: 'Alice', age: 30 },\n  { name: 'Bob', age: 25 },\n  { name: 'Carol', age: 35 },\n]);\n\nconsole.warn('This is a warning');\nconsole.error('This is an error');\nconsole.info('This is info');`
  );
  const [output, setOutput] = useState<LogEntry[]>([]);
  const [lang, setLang] = useState('javascript');
  const [execTime, setExecTime] = useState(0);

  const runCode = useCallback(() => {
    if (lang !== 'javascript') {
      setOutput([
        {
          type: 'error',
          message: `Only JavaScript execution is supported. You selected: ${lang}`,
          timestamp: Date.now(),
        },
      ]);
      return;
    }

    const logs: LogEntry[] = [];
    const timers: Record<string, number> = {};

    const consoleMock = {
      log: (...args: any[]) => {
        logs.push({
          type: 'log',
          message: args
            .map((a) => {
              if (typeof a === 'object')
                try {
                  return JSON.stringify(a, null, 2);
                } catch {
                  return String(a);
                }
              return String(a);
            })
            .join(' '),
          timestamp: Date.now(),
        });
      },
      error: (...args: any[]) => {
        logs.push({
          type: 'error',
          message: args.map((a) => String(a)).join(' '),
          timestamp: Date.now(),
        });
      },
      warn: (...args: any[]) => {
        logs.push({
          type: 'warn',
          message: args.map((a) => String(a)).join(' '),
          timestamp: Date.now(),
        });
      },
      info: (...args: any[]) => {
        logs.push({
          type: 'info',
          message: args.map((a) => String(a)).join(' '),
          timestamp: Date.now(),
        });
      },
      table: (data: any) => {
        if (!data || !Array.isArray(data)) {
          logs.push({ type: 'log', message: String(data), timestamp: Date.now() });
          return;
        }
        const keys = [...new Set(data.flatMap(Object.keys))];
        const colWidths = keys.map((k) =>
          Math.max(k.length, ...data.map((r: any) => String(r[k] ?? '').length))
        );
        const makeRow = (cells: string[]) =>
          '| ' + cells.map((c, i) => c.padEnd(colWidths[i])).join(' | ') + ' |';
        const sep = '+-' + colWidths.map((w) => '-'.repeat(w)).join('-+-') + '-+';
        let table = sep + '\n' + makeRow(keys) + '\n' + sep + '\n';
        for (const row of data) {
          table += makeRow(keys.map((k) => String(row[k] ?? ''))) + '\n';
        }
        table += sep;
        logs.push({ type: 'table', message: table, timestamp: Date.now() });
      },
      time: (label: string) => {
        timers[label] = performance.now();
      },
      timeEnd: (label: string) => {
        const start = timers[label];
        if (start) {
          logs.push({
            type: 'time',
            message: `${label}: ${(performance.now() - start).toFixed(2)}ms`,
            timestamp: Date.now(),
          });
          delete timers[label];
        }
      },
    };

    const startTime = performance.now();
    try {
      const fn = new Function('console', '\n"use strict";\n' + code + '\nreturn undefined;\n');
      fn(consoleMock);
      setExecTime(performance.now() - startTime);
      setOutput(
        logs.length > 0 ? logs : [{ type: 'log', message: '(no output)', timestamp: Date.now() }]
      );
    } catch (e: any) {
      setExecTime(performance.now() - startTime);
      logs.push({ type: 'error', message: `${e.name}: ${e.message}`, timestamp: Date.now() });
      setOutput(logs);
    }
  }, [code, lang]);

  const logColors: Record<string, string> = {
    log: 'text-blue-200/70',
    error: 'text-red-400',
    warn: 'text-yellow-400',
    info: 'text-cyan-400',
    table: 'text-blue-200/80 font-mono text-[10px]',
    time: 'text-green-400',
  };

  const logIcons: Record<string, any> = {
    error: <AlertCircle size={10} className="text-red-400 flex-shrink-0 mt-0.5" />,
    warn: <AlertCircle size={10} className="text-yellow-400 flex-shrink-0 mt-0.5" />,
    info: <CheckCircle size={10} className="text-cyan-400 flex-shrink-0 mt-0.5" />,
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80">
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-blue-500/10 bg-[#111d2e]">
        <FileText size={14} className="text-blue-400/50" />
        <select
          value={lang}
          onChange={(e) => setLang(e.target.value)}
          className="bg-[#162032] border border-blue-500/15 rounded px-2 py-0.5 text-xs outline-none"
        >
          <option value="javascript">JavaScript</option>
          <option value="typescript">TypeScript</option>
          <option value="python">Python</option>
          <option value="html">HTML</option>
          <option value="css">CSS</option>
        </select>
        <div className="flex-1" />
        {execTime > 0 && (
          <span className="text-[10px] text-blue-400/30 flex items-center gap-1">
            <Clock size={10} />
            {execTime.toFixed(1)}ms
          </span>
        )}
        <button
          onClick={runCode}
          className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-green-500/15 text-green-400 hover:bg-green-500/25 text-xs transition-colors"
        >
          <Play size={12} /> Run
        </button>
        <button
          onClick={() => navigator.clipboard.writeText(code)}
          className="p-1 rounded hover:bg-blue-500/20 text-blue-300/50"
          title="Copy code"
        >
          <Copy size={13} />
        </button>
        <button
          onClick={() => {
            setCode('');
            setOutput([]);
            setExecTime(0);
          }}
          className="p-1 rounded hover:bg-red-500/20 text-blue-300/50"
          title="Clear"
        >
          <Trash2 size={13} />
        </button>
      </div>
      <div className="flex-1 flex">
        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          className="flex-1 bg-[#0d1926] text-blue-100/80 p-3 text-xs font-mono resize-none outline-none border-r border-blue-500/10 leading-relaxed"
          spellCheck={false}
          placeholder="// Write your JavaScript code here..."
        />
        <div className="w-2/5 bg-[#0a1420] flex flex-col overflow-hidden">
          <div className="text-[10px] uppercase tracking-wider text-blue-400/30 px-3 py-2 border-b border-blue-500/5 flex items-center justify-between">
            <span>Console</span>
            <span className="text-blue-400/20">
              {output.length} {output.length === 1 ? 'entry' : 'entries'}
            </span>
          </div>
          <div className="flex-1 overflow-auto p-3 space-y-1.5">
            {output.length === 0 && (
              <div className="text-xs text-blue-400/20 italic">Run code to see output...</div>
            )}
            {output.map((log, i) => (
              <div
                key={i}
                className={`flex gap-1.5 ${log.type === 'table' ? 'overflow-x-auto' : ''}`}
              >
                {logIcons[log.type] || null}
                <pre
                  className={`text-xs whitespace-pre-wrap break-words ${logColors[log.type] || 'text-blue-200/70'} font-mono`}
                >
                  {log.message}
                </pre>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
