import React, { useState } from 'react';
import { Table } from 'lucide-react';

const COLS = 8;
const ROWS = 20;
const COL_LABELS = 'ABCDEFGH'.split('');

export default function Spreadsheet() {
  const [cells, setCells] = useState<Record<string, string>>({});
  const [selected, setSelected] = useState('A1');
  const [editValue, setEditValue] = useState('');

  const getCell = (col: number, row: number) => cells[`${COL_LABELS[col]}${row + 1}`] || '';

  const setCell = (key: string, value: string) => {
    setCells((prev) => ({ ...prev, [key]: value }));
  };

  const startEdit = (key: string) => {
    setSelected(key);
    setEditValue(cells[key] || '');
  };
  const commitEdit = () => {
    setCell(selected, editValue);
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80">
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-blue-500/10 bg-[#111d2e]">
        <Table size={14} className="text-blue-400/50" />
        <span className="text-xs text-blue-300/40">{selected}</span>
        <input
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onBlur={commitEdit}
          onKeyDown={(e) => e.key === 'Enter' && commitEdit()}
          className="flex-1 bg-[#162032] border border-blue-500/15 rounded px-2 py-0.5 text-xs outline-none"
        />
      </div>
      <div className="flex-1 overflow-auto">
        <div className="grid" style={{ gridTemplateColumns: `40px repeat(${COLS}, 80px)` }}>
          <div className="sticky top-0 left-0 bg-[#111d2e] z-10 border-r border-b border-blue-500/10" />
          {COL_LABELS.map((l) => (
            <div
              key={l}
              className="sticky top-0 bg-[#111d2e] text-center py-1 text-[10px] text-blue-300/30 border-r border-b border-blue-500/10"
            >
              {l}
            </div>
          ))}
          {Array.from({ length: ROWS }).map((_, r) => (
            <React.Fragment key={r}>
              <div className="sticky left-0 bg-[#111d2e] text-center py-0.5 text-[10px] text-blue-300/30 border-r border-b border-blue-500/10">
                {r + 1}
              </div>
              {Array.from({ length: COLS }).map((_, c) => {
                const key = `${COL_LABELS[c]}${r + 1}`;
                return (
                  <div
                    key={key}
                    onClick={() => startEdit(key)}
                    className={`border-r border-b border-blue-500/5 px-1 py-0.5 text-xs cursor-pointer ${selected === key ? 'ring-1 ring-blue-500 bg-blue-500/5' : 'hover:bg-blue-500/5'}`}
                  >
                    {getCell(c, r)}
                  </div>
                );
              })}
            </React.Fragment>
          ))}
        </div>
      </div>
    </div>
  );
}
