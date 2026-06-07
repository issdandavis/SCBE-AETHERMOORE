import React, { useState, useCallback, useMemo } from 'react';
import { FileText, Copy, Check, Eye, Code, Download } from 'lucide-react';

function parseMarkdown(md: string): string {
  let html = md
    // Code blocks
    .replace(
      /```(\w+)?\n([\s\S]*?)```/g,
      (_, lang, code) =>
        `<pre class="bg-[#0a1420] rounded-lg p-3 my-2 overflow-x-auto border border-blue-500/5"><code class="text-xs text-blue-200/60 font-mono">${escapeHtml(code)}</code></pre>`
    )
    // Inline code
    .replace(
      /`([^`]+)`/g,
      '<code class="bg-[#0a1420] px-1.5 py-0.5 rounded text-[11px] text-yellow-300/70 font-mono">$1</code>'
    )
    // Headers
    .replace(
      /^###### (.+)$/gm,
      '<h6 class="text-xs text-blue-300/40 font-semibold mt-3 mb-1">$1</h6>'
    )
    .replace(
      /^##### (.+)$/gm,
      '<h5 class="text-sm text-blue-300/50 font-semibold mt-3 mb-1">$1</h5>'
    )
    .replace(
      /^#### (.+)$/gm,
      '<h4 class="text-sm text-blue-300/60 font-semibold mt-3 mb-1">$1</h4>'
    )
    .replace(
      /^### (.+)$/gm,
      '<h3 class="text-base text-blue-200/80 font-semibold mt-4 mb-2">$1</h3>'
    )
    .replace(
      /^## (.+)$/gm,
      '<h2 class="text-lg text-blue-200 font-semibold mt-5 mb-2 pb-1 border-b border-blue-500/10">$1</h2>'
    )
    .replace(
      /^# (.+)$/gm,
      '<h1 class="text-xl text-blue-100 font-bold mt-6 mb-3 pb-2 border-b border-blue-500/20">$1</h1>'
    )
    // Bold + italic
    .replace(/\*\*\*([^*]+)\*\*\*/g, '<strong><em>$1</em></strong>')
    // Bold
    .replace(/\*\*([^*]+)\*\*/g, '<strong class="text-blue-100">$1</strong>')
    // Italic
    .replace(/\*([^*]+)\*/g, '<em class="text-blue-200/80">$1</em>')
    // Strikethrough
    .replace(/~~([^~]+)~~/g, '<del class="text-blue-300/30">$1</del>')
    // Blockquote
    .replace(
      /^&gt; (.+)$/gm,
      '<blockquote class="border-l-2 border-blue-500/30 pl-3 my-2 text-blue-200/50 italic">$1</blockquote>'
    )
    // Unordered lists
    .replace(
      /^- (.+)$/gm,
      '<li class="ml-4 text-blue-200/60 text-xs leading-relaxed list-disc">$1</li>'
    )
    // Ordered lists
    .replace(
      /^\d+\. (.+)$/gm,
      '<li class="ml-4 text-blue-200/60 text-xs leading-relaxed list-decimal">$1</li>'
    )
    // Checkbox lists
    .replace(
      /^- \[x\] (.+)$/gim,
      '<li class="ml-4 text-blue-200/60 text-xs"><input type="checkbox" checked disabled class="mr-1 accent-blue-500"/>$1</li>'
    )
    .replace(
      /^- \[ \] (.+)$/gim,
      '<li class="ml-4 text-blue-200/60 text-xs"><input type="checkbox" disabled class="mr-1"/>$1</li>'
    )
    // Links
    .replace(
      /\[([^\]]+)\]\(([^)]+)\)/g,
      '<a href="$2" target="_blank" class="text-blue-400 hover:text-blue-300 underline decoration-blue-500/30">$1</a>'
    )
    // Images
    .replace(
      /!\[([^\]]*)\]\(([^)]+)\)/g,
      '<img src="$2" alt="$1" class="max-w-full rounded-lg my-2 border border-blue-500/10" />'
    )
    // Horizontal rule
    .replace(/^---+$/gm, '<hr class="border-blue-500/10 my-4"/>')
    // Tables
    .replace(/\|(.+)\|\n\|[-:\|\s]+\|\n((?:\|.+\|\n?)+)/g, (_, header, rows) => {
      const hCells = header
        .split('|')
        .filter(Boolean)
        .map((c: string) => c.trim());
      const rLines = rows.trim().split('\n');
      const rCells = rLines.map((r: string) =>
        r
          .split('|')
          .filter(Boolean)
          .map((c: string) => c.trim())
      );
      return `<table class="w-full text-xs my-2 border border-blue-500/10 rounded-lg overflow-hidden"><thead class="bg-[#162032]"><tr>${hCells.map((c: string) => `<th class="px-2 py-1.5 text-left text-blue-200/60 font-semibold">${c}</th>`).join('')}</tr></thead><tbody>${rCells.map((row: string[]) => `<tr class="border-t border-blue-500/5">${row.map((c: string) => `<td class="px-2 py-1 text-blue-200/50">${c}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
    })
    // Paragraphs (must be last)
    .split('\n\n')
    .map((p) => p.trim())
    .filter(Boolean)
    .map((p) => {
      if (p.startsWith('<')) return p;
      return `<p class="text-xs text-blue-200/60 leading-relaxed mb-2">${p}</p>`;
    })
    .join('\n');

  return html;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

const SAMPLE_MD = `# Welcome to Markdown Preview

This is a **live** markdown previewer with support for:

## Features

- **Bold** and *italic* text
- \`inline code\` and code blocks
- [Links](https://example.com)
- Tables and lists

## Code Example

\`\`\`javascript
function hello() {
  return "Hello, World!";
}
\`\`\`

> Blockquote: Markdown is awesome!

| Feature | Status |
|---------|--------|
| Bold | OK |
| Tables | OK |
| Code | OK |
`;

export default function MarkdownPreview() {
  const [markdown, setMarkdown] = useState(SAMPLE_MD);
  const [mode, setMode] = useState<'split' | 'preview' | 'code'>('split');
  const [copied, setCopied] = useState(false);

  const html = useMemo(() => parseMarkdown(markdown), [markdown]);

  const copy = useCallback(() => {
    navigator.clipboard.writeText(html);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }, [html]);

  const download = () => {
    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'document.md';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-blue-500/10">
        <FileText size={16} className="text-blue-400" />
        <h2 className="text-sm text-blue-200 font-semibold">Markdown Preview</h2>
        <div className="flex-1" />
        {(['split', 'preview', 'code'] as const).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`px-2 py-1 rounded text-[10px] transition-colors ${mode === m ? 'bg-blue-500/20 text-blue-200' : 'text-blue-300/30 hover:text-blue-200/60'}`}
          >
            {m === 'split' ? 'Split' : m === 'preview' ? 'Preview' : 'Code'}
          </button>
        ))}
        <button
          onClick={copy}
          className="p-1 rounded hover:bg-blue-500/20 text-blue-300/40 hover:text-blue-300 transition-colors ml-1"
        >
          {copied ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
        </button>
        <button
          onClick={download}
          className="p-1 rounded hover:bg-blue-500/20 text-blue-300/40 hover:text-blue-300 transition-colors"
        >
          <Download size={12} />
        </button>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {(mode === 'split' || mode === 'code') && (
          <div
            className={`${mode === 'split' ? 'flex-1' : 'flex-1'} border-r border-blue-500/10 flex flex-col`}
          >
            <div className="text-[10px] uppercase tracking-wider text-blue-400/30 px-3 py-1.5 border-b border-blue-500/5 flex items-center gap-1">
              <Code size={10} /> Markdown
            </div>
            <textarea
              value={markdown}
              onChange={(e) => setMarkdown(e.target.value)}
              className="flex-1 bg-[#0d1926] p-3 text-xs font-mono resize-none outline-none text-blue-100/70 leading-relaxed"
              spellCheck={false}
              placeholder="Write markdown here..."
            />
          </div>
        )}
        {(mode === 'split' || mode === 'preview') && (
          <div
            className={`${mode === 'split' ? 'flex-1' : 'flex-1'} flex flex-col overflow-hidden`}
          >
            <div className="text-[10px] uppercase tracking-wider text-blue-400/30 px-3 py-1.5 border-b border-blue-500/5 flex items-center gap-1">
              <Eye size={10} /> Preview
            </div>
            <div
              className="flex-1 overflow-y-auto p-3"
              dangerouslySetInnerHTML={{ __html: html }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
