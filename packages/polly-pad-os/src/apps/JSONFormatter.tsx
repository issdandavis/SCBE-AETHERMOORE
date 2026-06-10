import React, { useState, useCallback, useMemo } from 'react';
import {
  FileJson,
  Copy,
  Check,
  TreePine,
  AlignLeft,
  Wand2,
  AlertCircle,
  Download,
} from 'lucide-react';

interface JSONNodeProps {
  data: any;
  keyName?: string;
  depth?: number;
  expanded?: boolean;
}

function JSONNode({ data, keyName, depth = 0, expanded = true }: JSONNodeProps) {
  const [isOpen, setIsOpen] = useState(expanded);
  const indent = '  '.repeat(depth);

  if (data === null) return <span className="text-blue-400/50">null</span>;
  if (typeof data === 'boolean') return <span className="text-purple-300">{String(data)}</span>;
  if (typeof data === 'number') return <span className="text-yellow-300/80">{data}</span>;
  if (typeof data === 'string') return <span className="text-green-300/80">"{data}"</span>;

  if (Array.isArray(data)) {
    if (data.length === 0) return <span className="text-blue-300/40">[]</span>;
    return (
      <span>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="text-blue-300/40 hover:text-blue-200 transition-colors"
        >
          {isOpen ? '▼' : '▶'} [{data.length}]
        </button>
        {isOpen && (
          <>
            {'['}\n
            {data.map((item, i) => (
              <div key={i} className="block">
                {indent} <JSONNode data={item} depth={depth + 1} />
                {i < data.length - 1 ? ',' : ''}
              </div>
            ))}
            {indent}]
          </>
        )}
        {!isOpen && ' [...] '}
      </span>
    );
  }

  if (typeof data === 'object') {
    const keys = Object.keys(data);
    if (keys.length === 0) return <span className="text-blue-300/40">{'{}'}</span>;
    return (
      <span>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="text-blue-300/40 hover:text-blue-200 transition-colors"
        >
          {isOpen ? '▼' : '▶'} {'{'}
          {keys.length}
          {'}'}
        </button>
        {isOpen && (
          <>
            {'{'}
            {'\n'}
            {keys.map((k, i) => (
              <div key={k} className="block">
                {indent} <span className="text-blue-200/60">"{k}"</span>:{' '}
                <JSONNode data={data[k]} keyName={k} depth={depth + 1} />
                {i < keys.length - 1 ? ',' : ''}
              </div>
            ))}
            {indent}
            {'}'}
          </>
        )}
        {!isOpen && ' {...} '}
      </span>
    );
  }

  return <span>{String(data)}</span>;
}

export default function JSONFormatter() {
  const [input, setInput] = useState('');
  const [mode, setMode] = useState<'tree' | 'formatted' | 'minify'>('tree');
  const [copied, setCopied] = useState(false);

  const parseResult = useMemo(() => {
    if (!input.trim()) return { valid: true, data: null, error: '' };
    try {
      const parsed = JSON.parse(input);
      return { valid: true, data: parsed, error: '' };
    } catch (e: any) {
      return { valid: false, data: null, error: e.message };
    }
  }, [input]);

  const formatted = useMemo(() => {
    if (!parseResult.data) return '';
    if (mode === 'formatted') return JSON.stringify(parseResult.data, null, 2);
    if (mode === 'minify') return JSON.stringify(parseResult.data);
    return '';
  }, [parseResult.data, mode]);

  const stats = useMemo(() => {
    if (!parseResult.data) return null;
    const countKeys = (obj: any): number => {
      if (typeof obj !== 'object' || obj === null) return 0;
      if (Array.isArray(obj))
        return obj.reduce(
          (sum, v) =>
            sum + countKeys(v) + (typeof v === 'object' && v !== null ? Object.keys(v).length : 0),
          0
        );
      return Object.keys(obj).reduce((sum, k) => sum + 1 + countKeys(obj[k]), 0);
    };
    return {
      keys: countKeys(parseResult.data),
      size: new Blob([JSON.stringify(parseResult.data)]).size,
      type: Array.isArray(parseResult.data) ? 'array' : typeof parseResult.data,
      length: Array.isArray(parseResult.data)
        ? parseResult.data.length
        : Object.keys(parseResult.data || {}).length,
    };
  }, [parseResult.data]);

  const copy = useCallback(() => {
    const text = mode === 'tree' ? JSON.stringify(parseResult.data, null, 2) : formatted;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }, [formatted, mode, parseResult.data]);

  const download = () => {
    const text = mode === 'tree' ? JSON.stringify(parseResult.data, null, 2) : formatted;
    const blob = new Blob([text], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'formatted.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  const sampleJSON = () => {
    setInput(
      JSON.stringify(
        {
          name: 'SCBE Desktop',
          version: '2.0',
          features: ['Desktop', 'Terminal', 'Browser', 'Code Editor'],
          config: { theme: 'dark', language: 'en', notifications: true },
          users: [
            { id: 1, name: 'Admin', role: 'admin' },
            { id: 2, name: 'Guest', role: 'user' },
          ],
        },
        null,
        2
      )
    );
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-blue-500/10">
        <FileJson size={16} className="text-blue-400" />
        <h2 className="text-sm text-blue-200 font-semibold">JSON Formatter</h2>
        <div className="flex-1" />
        <button
          onClick={sampleJSON}
          className="px-2 py-1 rounded bg-blue-500/10 text-blue-300/50 hover:text-blue-200 text-[10px] transition-colors flex items-center gap-1"
        >
          <Wand2 size={10} /> Sample
        </button>
      </div>

      <div className="flex gap-1 p-2 border-b border-blue-500/5">
        {(['tree', 'formatted', 'minify'] as const).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`px-3 py-1 rounded-lg text-xs transition-colors flex items-center gap-1 ${mode === m ? 'bg-blue-500/20 text-blue-200' : 'text-blue-300/30 hover:text-blue-200/60'}`}
          >
            {m === 'tree' ? (
              <TreePine size={10} />
            ) : m === 'formatted' ? (
              <AlignLeft size={10} />
            ) : (
              <FileJson size={10} />
            )}
            {m === 'tree' ? 'Tree' : m === 'formatted' ? 'Pretty' : 'Minify'}
          </button>
        ))}
        <div className="flex-1" />
        {parseResult.valid && parseResult.data && (
          <>
            <button
              onClick={copy}
              className="p-1 rounded hover:bg-blue-500/20 text-blue-300/40 hover:text-blue-300 transition-colors"
            >
              {copied ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
            </button>
            <button
              onClick={download}
              className="p-1 rounded hover:bg-blue-500/20 text-blue-300/40 hover:text-blue-300 transition-colors"
            >
              <Download size={12} />
            </button>
          </>
        )}
      </div>

      <div className="flex-1 flex">
        <div className="flex-1 flex flex-col border-r border-blue-500/10">
          <div className="text-[10px] uppercase tracking-wider text-blue-400/30 px-3 py-1.5 border-b border-blue-500/5">
            Input
          </div>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Paste JSON here..."
            className="flex-1 bg-[#0d1926] text-blue-100/70 p-3 text-xs font-mono resize-none outline-none leading-relaxed"
            spellCheck={false}
          />
          {!parseResult.valid && input.trim() && (
            <div className="px-3 py-1.5 border-t border-red-500/10 flex items-center gap-1.5 text-[10px] text-red-400/70">
              <AlertCircle size={10} />
              {parseResult.error}
            </div>
          )}
        </div>

        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="text-[10px] uppercase tracking-wider text-blue-400/30 px-3 py-1.5 border-b border-blue-500/5 flex items-center justify-between">
            <span>Output</span>
            {stats && (
              <div className="flex gap-2 text-blue-400/20">
                <span>{stats.type}</span>
                <span>{stats.length} items</span>
                <span>{stats.keys} keys</span>
                <span>{(stats.size / 1024).toFixed(1)} KB</span>
              </div>
            )}
          </div>
          <div className="flex-1 overflow-auto p-3 text-xs font-mono leading-relaxed">
            {parseResult.valid && parseResult.data ? (
              mode === 'tree' ? (
                <div className="whitespace-pre">
                  <JSONNode data={parseResult.data} />
                </div>
              ) : (
                <pre className="whitespace-pre-wrap break-all">{formatted}</pre>
              )
            ) : (
              <div className="text-blue-400/20 italic">Valid JSON will appear here...</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
