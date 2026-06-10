import React, { useState } from 'react';
import { RotateCcw, Check, Lightbulb } from 'lucide-react';

const PUZZLE = [
  [5, 3, 0, 0, 7, 0, 0, 0, 0],
  [6, 0, 0, 1, 9, 5, 0, 0, 0],
  [0, 9, 8, 0, 0, 0, 0, 6, 0],
  [8, 0, 0, 0, 6, 0, 0, 0, 3],
  [4, 0, 0, 8, 0, 3, 0, 0, 1],
  [7, 0, 0, 0, 2, 0, 0, 0, 6],
  [0, 6, 0, 0, 0, 0, 2, 8, 0],
  [0, 0, 0, 4, 1, 9, 0, 0, 5],
  [0, 0, 0, 0, 8, 0, 0, 7, 9],
];
const SOLUTION = [
  [5, 3, 4, 6, 7, 8, 9, 1, 2],
  [6, 7, 2, 1, 9, 5, 3, 4, 8],
  [1, 9, 8, 3, 4, 2, 5, 6, 7],
  [8, 5, 9, 7, 6, 1, 4, 2, 3],
  [4, 2, 6, 8, 5, 3, 7, 9, 1],
  [7, 1, 3, 9, 2, 4, 8, 5, 6],
  [9, 6, 1, 5, 3, 7, 2, 8, 4],
  [2, 8, 7, 4, 1, 9, 6, 3, 5],
  [3, 4, 5, 2, 8, 6, 1, 7, 9],
];

export default function Sudoku() {
  const [grid, setGrid] = useState(() => PUZZLE.map((r) => [...r]));
  const [selected, setSelected] = useState<{ r: number; c: number } | null>(null);
  const [checkResult, setCheckResult] = useState<string | null>(null);

  const handleCellClick = (r: number, c: number) => {
    if (PUZZLE[r][c] !== 0) return;
    setSelected({ r, c });
    setCheckResult(null);
  };

  const handleNumber = (num: number) => {
    if (!selected) return;
    const { r, c } = selected;
    if (PUZZLE[r][c] !== 0) return;
    const newGrid = grid.map((row) => [...row]);
    newGrid[r][c] = num;
    setGrid(newGrid);
  };

  const checkSolution = () => {
    let correct = 0,
      total = 0;
    for (let r = 0; r < 9; r++)
      for (let c = 0; c < 9; c++)
        if (PUZZLE[r][c] === 0) {
          total++;
          if (grid[r][c] === SOLUTION[r][c]) correct++;
        }
    if (correct === total && total > 0) setCheckResult('Perfect! All correct!');
    else setCheckResult(`${correct}/${total} cells correct`);
  };

  const getHint = () => {
    if (!selected) return;
    const { r, c } = selected;
    handleNumber(SOLUTION[r][c]);
  };

  const reset = () => {
    setGrid(PUZZLE.map((r) => [...r]));
    setSelected(null);
    setCheckResult(null);
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 items-center justify-center p-3">
      <div className="flex items-center justify-between w-full max-w-[360px] mb-3">
        <button onClick={reset} className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/50">
          <RotateCcw size={14} />
        </button>
        <h2 className="text-sm text-blue-200">Sudoku</h2>
        <button
          onClick={getHint}
          className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/50"
          title="Hint"
        >
          <Lightbulb size={14} />
        </button>
        <button
          onClick={checkSolution}
          className="p-1.5 rounded hover:bg-green-500/20 text-blue-300/50"
          title="Check"
        >
          <Check size={14} />
        </button>
      </div>
      <div
        className="grid grid-cols-9 gap-px bg-blue-500/20 p-px rounded-lg"
        style={{ border: '2px solid rgba(59,130,246,0.2)' }}
      >
        {grid.map((row, r) =>
          row.map((cell, c) => {
            const isFixed = PUZZLE[r][c] !== 0;
            const isSelected = selected?.r === r && selected?.c === c;
            const isSameBox =
              selected &&
              Math.floor(selected.r / 3) === Math.floor(r / 3) &&
              Math.floor(selected.c / 3) === Math.floor(c / 3);
            const isSameRow = selected?.r === r;
            const isSameCol = selected?.c === c;
            return (
              <button
                key={`${r}-${c}`}
                onClick={() => handleCellClick(r, c)}
                className={`w-9 h-9 flex items-center justify-center text-sm font-medium transition-all ${
                  isFixed ? 'text-blue-200/80' : 'text-blue-400'
                } ${isSelected ? 'bg-blue-500/30' : isSameBox || isSameRow || isSameCol ? 'bg-blue-500/8' : 'bg-[#0d1926]'} ${
                  (c + 1) % 3 === 0 && c < 8 ? 'border-r border-blue-500/20' : ''
                } ${(r + 1) % 3 === 0 && r < 8 ? 'border-b border-blue-500/20' : ''}`}
              >
                {cell !== 0 ? cell : ''}
              </button>
            );
          })
        )}
      </div>
      <div className="grid grid-cols-9 gap-1 mt-3 max-w-[340px]">
        {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => (
          <button
            key={n}
            onClick={() => handleNumber(n)}
            className="h-8 rounded bg-[#162032] hover:bg-blue-500/20 text-blue-200 text-sm transition-colors"
          >
            {n}
          </button>
        ))}
      </div>
      {checkResult && <p className="mt-2 text-xs text-green-400">{checkResult}</p>}
    </div>
  );
}
