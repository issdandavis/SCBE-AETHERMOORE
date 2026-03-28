
import React, { useEffect, useState } from 'react';

interface CodeEditorProps {
  code: string;
  onChange: (value: string) => void;
  language?: string;
  readOnly?: boolean;
}

export const CodeEditor: React.FC<CodeEditorProps> = ({ code, onChange, readOnly = false }) => {
  const [lines, setLines] = useState(1);

  useEffect(() => {
    setLines(code.split('\n').length);
  }, [code]);

  return (
    <div className="flex h-full w-full bg-[#1e1e1e] font-mono text-sm overflow-hidden">
      {/* Line Numbers */}
      <div className="w-12 bg-[#1e1e1e] border-r border-[#333] text-[#858585] text-right pr-3 pt-4 select-none flex flex-col items-end leading-6">
        {Array.from({ length: Math.max(lines, 20) }).map((_, i) => (
          <div key={i}>{i + 1}</div>
        ))}
      </div>
      
      {/* Editor */}
      <textarea
        value={code}
        onChange={(e) => onChange(e.target.value)}
        readOnly={readOnly}
        spellCheck={false}
        className="flex-1 bg-transparent text-[#d4d4d4] p-4 outline-none resize-none leading-6 w-full h-full whitespace-pre font-inherit"
        style={{ tabSize: 4 }}
      />
    </div>
  );
};
