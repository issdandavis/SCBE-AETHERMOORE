import React, { useState, useEffect, useCallback } from 'react';
import { RotateCcw, Trophy } from 'lucide-react';

const SIZE = 4;
const COLORS: Record<number, string> = {
  2: 'bg-blue-500/20 text-blue-200',
  4: 'bg-blue-500/30 text-blue-100',
  8: 'bg-indigo-500/30 text-indigo-200',
  16: 'bg-purple-500/30 text-purple-200',
  32: 'bg-pink-500/30 text-pink-200',
  64: 'bg-rose-500/30 text-rose-200',
  128: 'bg-orange-500/30 text-orange-200',
  256: 'bg-amber-500/30 text-amber-200',
  512: 'bg-yellow-500/30 text-yellow-200',
  1024: 'bg-emerald-500/30 text-emerald-200',
  2048: 'bg-green-500/30 text-green-200',
};

function addRandom(grid: number[][]): number[][] {
  const empty: [number, number][] = [];
  for (let r = 0; r < SIZE; r++) for (let c = 0; c < SIZE; c++) if (!grid[r][c]) empty.push([r, c]);
  if (empty.length === 0) return grid;
  const [r, c] = empty[Math.floor(Math.random() * empty.length)];
  const ng = grid.map((row) => [...row]);
  ng[r][c] = Math.random() < 0.9 ? 2 : 4;
  return ng;
}

function initGrid() {
  let g = Array.from({ length: SIZE }, () => Array(SIZE).fill(0));
  g = addRandom(g);
  g = addRandom(g);
  return g;
}

function slideRow(row: number[]) {
  let filtered = row.filter((x) => x);
  for (let i = 0; i < filtered.length - 1; i++)
    if (filtered[i] === filtered[i + 1]) {
      filtered[i] *= 2;
      filtered[i + 1] = 0;
    }
  filtered = filtered.filter((x) => x);
  while (filtered.length < SIZE) filtered.push(0);
  return filtered;
}

export default function Game2048() {
  const [grid, setGrid] = useState(initGrid);
  const [score, setScore] = useState(0);
  const [highScore, setHighScore] = useState(() =>
    parseInt(localStorage.getItem('2048_hs') || '0')
  );
  const [over, setOver] = useState(false);

  const move = useCallback(
    (dir: 'left' | 'right' | 'up' | 'down') => {
      setGrid((prev) => {
        let ng = prev.map((r) => [...r]);
        if (dir === 'left') ng = ng.map((r) => slideRow(r));
        else if (dir === 'right') ng = ng.map((r) => slideRow([...r].reverse()).reverse());
        else if (dir === 'up') {
          for (let c = 0; c < SIZE; c++) {
            const col = slideRow(ng.map((r) => r[c]));
            for (let r = 0; r < SIZE; r++) ng[r][c] = col[r];
          }
        } else {
          for (let c = 0; c < SIZE; c++) {
            const col = slideRow(ng.map((r) => r[c]).reverse()).reverse();
            for (let r = 0; r < SIZE; r++) ng[r][c] = col[r];
          }
        }
        const changed = ng.some((row, r) => row.some((c, i) => c !== prev[r][i]));
        if (!changed) return prev;
        ng = addRandom(ng);
        const max = Math.max(...ng.flat());
        setScore((s) => {
          const ns = s + max;
          if (ns > highScore) {
            setHighScore(ns);
            localStorage.setItem('2048_hs', String(ns));
          }
          return ns;
        });
        const canMove = ng.some((row, r) =>
          row.some(
            (c, i) =>
              !c || (i < SIZE - 1 && row[i] === row[i + 1]) || (r < SIZE - 1 && c === ng[r + 1][i])
          )
        );
        if (!canMove) setOver(true);
        return ng;
      });
    },
    [highScore]
  );

  useEffect(() => {
    const handle = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowLeft':
          move('left');
          break;
        case 'ArrowRight':
          move('right');
          break;
        case 'ArrowUp':
          move('up');
          break;
        case 'ArrowDown':
          move('down');
          break;
      }
    };
    window.addEventListener('keydown', handle);
    return () => window.removeEventListener('keydown', handle);
  }, [move]);

  const reset = () => {
    setGrid(initGrid());
    setScore(0);
    setOver(false);
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 items-center justify-center p-3">
      <div className="flex items-center justify-between w-full max-w-[340px] mb-3">
        <div className="text-xs text-blue-300/50">
          Score: <span className="text-blue-200">{score}</span>
        </div>
        <div className="flex items-center gap-1 text-xs text-blue-300/30">
          <Trophy size={12} />
          {highScore}
        </div>
        <button onClick={reset} className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/50">
          <RotateCcw size={14} />
        </button>
      </div>
      <div className="bg-[#0a1420] rounded-xl border border-blue-500/15 p-3">
        <div className="grid grid-cols-4 gap-2">
          {grid.flat().map((cell, i) => (
            <div
              key={i}
              className={`w-16 h-16 rounded-lg flex items-center justify-center text-lg font-bold transition-all ${cell ? COLORS[cell] || 'bg-blue-500/40 text-white' : 'bg-[#162032]'}`}
            >
              {cell || ''}
            </div>
          ))}
        </div>
      </div>
      {over && <p className="mt-3 text-red-400 text-sm">Game Over!</p>}
      <div className="grid grid-cols-3 gap-1 mt-3 w-28">
        <div />
        <button
          onClick={() => move('up')}
          className="h-8 rounded bg-blue-500/10 text-blue-300 text-xs"
        >
          ▲
        </button>
        <div />
        <button
          onClick={() => move('left')}
          className="h-8 rounded bg-blue-500/10 text-blue-300 text-xs"
        >
          ◀
        </button>
        <button
          onClick={() => move('down')}
          className="h-8 rounded bg-blue-500/10 text-blue-300 text-xs"
        >
          ▼
        </button>
        <button
          onClick={() => move('right')}
          className="h-8 rounded bg-blue-500/10 text-blue-300 text-xs"
        >
          ▶
        </button>
      </div>
    </div>
  );
}
