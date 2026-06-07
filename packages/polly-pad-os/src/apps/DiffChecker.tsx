import React, { useState } from 'react';

export default function DiffChecker() {
  const [left, setLeft] = useState('Line 1\nLine 2\nLine 3\nCommon line\nLine 5');
  const [right, setRight] = useState('Line 1\nModified 2\nLine 3\nCommon line\nLine 6');
  const [showDiff, setShowDiff] = useState(false);

  const leftLines = left.split('\n');
  const rightLines = right.split('\n');
  const maxLen = Math.max(leftLines.length, rightLines.length);

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 p-3">
      <div className="flex items-center gap-2 mb-3">
        <h2 className="text-sm text-blue-200 font-semibold">Diff Checker</h2>
        <button
          onClick={() => setShowDiff(!showDiff)}
          className="px-3 py-1 rounded-lg bg-blue-500/20 text-blue-200 text-xs hover:bg-blue-500/30 transition-colors"
        >
          {showDiff ? 'Edit' : 'Compare'}
        </button>
      </div>
      {!showDiff ? (
        <div className="flex-1 flex gap-3">
          <textarea
            value={left}
            onChange={(e) => setLeft(e.target.value)}
            placeholder="Original text..."
            className="flex-1 bg-[#162032] border border-blue-500/10 rounded-xl p-3 text-xs font-mono resize-none outline-none"
          />
          <textarea
            value={right}
            onChange={(e) => setRight(e.target.value)}
            placeholder="Modified text..."
            className="flex-1 bg-[#162032] border border-blue-500/10 rounded-xl p-3 text-xs font-mono resize-none outline-none"
          />
        </div>
      ) : (
        <div className="flex-1 overflow-auto">
          <div className="grid grid-cols-[auto_1fr_1fr] gap-x-4 text-xs">
            <div className="text-blue-300/20 text-right pr-2">#</div>
            <div className="text-blue-300/40 mb-1">Original</div>
            <div className="text-blue-300/40 mb-1">Modified</div>
            {Array.from({ length: maxLen }).map((_, i) => {
              const l = leftLines[i] || '';
              const r = rightLines[i] || '';
              const same = l === r;
              return (
                <React.Fragment key={i}>
                  <div className="text-blue-300/20 text-right pr-2">{i + 1}</div>
                  <div
                    className={`py-0.5 px-2 rounded ${same ? '' : 'bg-red-500/10 text-red-300/60'}`}
                  >
                    {l || ' '}
                  </div>
                  <div
                    className={`py-0.5 px-2 rounded ${same ? '' : 'bg-green-500/10 text-green-300/60'}`}
                  >
                    {r || ' '}
                  </div>
                </React.Fragment>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
