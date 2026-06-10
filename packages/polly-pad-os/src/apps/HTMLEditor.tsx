import React, { useState } from 'react';

const DEMO_HTML = `<!DOCTYPE html>\n<html>\n<head>\n  <style>\n    body { font-family: sans-serif; padding: 20px; }\n    h1 { color: #60a5fa; }\n  </style>\n</head>\n<body>\n  <h1>Hello SCBE Desktop!</h1>\n  <p>This is a live HTML preview.</p>\n  <button style="padding:10px 20px;background:#3b82f6;color:white;border:none;border-radius:5px;">\n    Click Me\n  </button>\n</body>\n</html>`;

export default function HTMLEditor() {
  const [code, setCode] = useState(DEMO_HTML);
  const [srcDoc, setSrcDoc] = useState(DEMO_HTML);

  const run = () => setSrcDoc(code);

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80">
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-blue-500/10 bg-[#111d2e]">
        <span className="text-xs text-blue-300/40">HTML Editor</span>
        <div className="flex-1" />
        <button
          onClick={run}
          className="px-3 py-1 rounded-lg bg-green-500/15 text-green-400 hover:bg-green-500/25 text-xs transition-colors"
        >
          Run
        </button>
      </div>
      <div className="flex-1 flex">
        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          className="flex-1 bg-[#0d1926] p-3 text-xs font-mono resize-none outline-none border-r border-blue-500/10"
          spellCheck={false}
        />
        <div className="flex-1 bg-white rounded-lg m-2 overflow-hidden">
          <iframe
            srcDoc={srcDoc}
            className="w-full h-full border-none"
            sandbox="allow-scripts"
            title="preview"
          />
        </div>
      </div>
    </div>
  );
}
