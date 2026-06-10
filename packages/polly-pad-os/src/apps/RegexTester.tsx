import React, { useState, useMemo, useCallback } from 'react';
import { Regex, Copy, Check, AlertCircle, Trash2 } from 'lucide-react';

const SAMPLE_TEXT = `Hello World! Contact us at support@linuxos.web or admin@example.com.
Phone numbers: +1-555-123-4567, (555) 987-6543
Visit https://linuxos.web or http://example.org/page?q=test
IP address: 192.168.1.1
Date: 2024-01-15, 15/01/2024
Price: $49.99, €29.50`;

const PRESET_PATTERNS = [
  { name: 'Email', pattern: '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}', flags: 'g' },
  { name: 'URL', pattern: 'https?://[^\\s]+', flags: 'gi' },
  {
    name: 'Phone',
    pattern: '[(+]?[0-9]{1,4}[)-]?[\\s]?[0-9]{3}[\\s.-]?[0-9]{3}[\\s.-]?[0-9]{4}',
    flags: 'g',
  },
  { name: 'IP Address', pattern: '\\b(?:[0-9]{1,3}\\.){3}[0-9]{1,3}\\b', flags: 'g' },
  { name: 'Date (YYYY-MM-DD)', pattern: '\\d{4}-\\d{2}-\\d{2}', flags: 'g' },
  { name: 'Price', pattern: '[$€£]\\d+(?:\\.\\d{2})?', flags: 'g' },
];

export default function RegexTester() {
  const [pattern, setPattern] = useState('[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}');
  const [flags, setFlags] = useState('g');
  const [text, setText] = useState(SAMPLE_TEXT);
  const [copied, setCopied] = useState(false);

  const result = useMemo(() => {
    if (!pattern.trim()) return { valid: true, matches: [], error: '', highlighted: text };
    try {
      const regex = new RegExp(pattern, flags);
      const matches: { text: string; index: number; groups: string[] }[] = [];
      let match;
      const globalFlags = flags.includes('g') ? flags : flags + 'g';
      const globalRegex = new RegExp(pattern, globalFlags);

      while ((match = globalRegex.exec(text)) !== null) {
        matches.push({ text: match[0], index: match.index, groups: match.slice(1) });
        if (!flags.includes('g')) break;
      }

      // Build highlighted HTML
      let highlighted = '';
      let lastIndex = 0;
      for (const m of matches) {
        highlighted += escapeHtml(text.slice(lastIndex, m.index));
        highlighted += `<mark class="bg-yellow-500/20 text-yellow-200 border-b border-yellow-500/30">${escapeHtml(m.text)}</mark>`;
        lastIndex = m.index + m.text.length;
      }
      highlighted += escapeHtml(text.slice(lastIndex));

      return { valid: true, matches, error: '', highlighted };
    } catch (e: any) {
      return { valid: false, matches: [], error: e.message, highlighted: escapeHtml(text) };
    }
  }, [pattern, flags, text]);

  const copy = useCallback(() => {
    navigator.clipboard.writeText(`/${pattern}/${flags}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }, [pattern, flags]);

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-blue-500/10">
        <Regex size={16} className="text-blue-400" />
        <h2 className="text-sm text-blue-200 font-semibold">Regex Tester</h2>
        <div className="flex-1" />
        <button
          onClick={copy}
          className="p-1 rounded hover:bg-blue-500/20 text-blue-300/40 hover:text-blue-300 transition-colors"
        >
          {copied ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
        </button>
      </div>

      <div className="p-3 space-y-3">
        {/* Pattern Input */}
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-blue-400/30 text-sm">
              /
            </span>
            <input
              value={pattern}
              onChange={(e) => setPattern(e.target.value)}
              placeholder="Enter regex pattern..."
              className={`w-full bg-[#162032] border rounded-xl pl-7 pr-3 py-2 text-sm font-mono outline-none transition-colors ${result.error ? 'border-red-500/30 focus:border-red-500/50' : 'border-blue-500/15 focus:border-blue-500/30'}`}
            />
          </div>
          <input
            value={flags}
            onChange={(e) => setFlags(e.target.value)}
            placeholder="flags"
            className="w-16 bg-[#162032] border border-blue-500/15 rounded-xl px-2 py-2 text-sm font-mono text-center outline-none focus:border-blue-500/30"
          />
        </div>

        {/* Error */}
        {result.error && (
          <div className="flex items-center gap-1.5 text-xs text-red-400/70">
            <AlertCircle size={12} />
            {result.error}
          </div>
        )}

        {/* Presets */}
        <div className="flex flex-wrap gap-1">
          {PRESET_PATTERNS.map((p) => (
            <button
              key={p.name}
              onClick={() => {
                setPattern(p.pattern);
                setFlags(p.flags);
              }}
              className="px-2 py-1 rounded-lg bg-[#162032] text-[10px] text-blue-200/40 hover:text-blue-200/70 hover:bg-blue-500/10 transition-colors"
            >
              {p.name}
            </button>
          ))}
        </div>

        {/* Flags toggle */}
        <div className="flex gap-2">
          {['g', 'i', 'm', 's', 'u'].map((f) => (
            <label key={f} className="flex items-center gap-1 cursor-pointer">
              <input
                type="checkbox"
                checked={flags.includes(f)}
                onChange={(e) => setFlags(e.target.checked ? flags + f : flags.replace(f, ''))}
                className="accent-blue-500"
              />
              <span className="text-[10px] text-blue-300/40">
                {f === 'g'
                  ? 'Global'
                  : f === 'i'
                    ? 'Ignore Case'
                    : f === 'm'
                      ? 'Multiline'
                      : f === 's'
                        ? 'Dot All'
                        : 'Unicode'}
              </span>
            </label>
          ))}
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Test Text */}
        <div className="flex-1 flex flex-col border-r border-blue-500/10">
          <div className="flex items-center justify-between px-3 py-1.5 border-b border-blue-500/5">
            <span className="text-[10px] uppercase tracking-wider text-blue-400/30">Test Text</span>
            <button
              onClick={() => setText('')}
              className="p-0.5 rounded hover:bg-red-500/20 text-blue-300/20 hover:text-red-400 transition-colors"
            >
              <Trash2 size={10} />
            </button>
          </div>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            className="flex-1 bg-[#0d1926] p-3 text-xs font-mono resize-none outline-none text-blue-100/70 leading-relaxed"
            spellCheck={false}
          />
        </div>

        {/* Highlighted Matches */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex items-center justify-between px-3 py-1.5 border-b border-blue-500/5">
            <span className="text-[10px] uppercase tracking-wider text-blue-400/30">
              Matches ({result.matches.length})
            </span>
          </div>
          <div className="flex-1 overflow-auto">
            <div
              className="p-3 text-xs font-mono leading-relaxed whitespace-pre-wrap"
              dangerouslySetInnerHTML={{ __html: result.highlighted }}
            />
          </div>
        </div>
      </div>

      {/* Match List */}
      {result.matches.length > 0 && (
        <div className="border-t border-blue-500/10 p-2 max-h-28 overflow-y-auto">
          <div className="text-[10px] uppercase tracking-wider text-blue-400/30 mb-1">Results</div>
          <div className="space-y-0.5">
            {result.matches.slice(0, 20).map((m, i) => (
              <div key={i} className="flex items-center gap-2 text-[10px]">
                <span className="text-blue-400/20 w-5 text-right">{i + 1}.</span>
                <span className="text-yellow-200/70 font-mono">{m.text}</span>
                <span className="text-blue-400/20">at {m.index}</span>
                {m.groups.length > 0 && m.groups.some((g) => g) && (
                  <span className="text-blue-300/30">
                    groups: {m.groups.filter(Boolean).join(', ')}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
