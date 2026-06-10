import React, { useState, useCallback } from 'react';
import { Flag, Bomb, RotateCcw } from 'lucide-react';

const ROWS = 10;
const COLS = 10;
const MINES = 15;

interface Cell {
  isMine: boolean;
  isRevealed: boolean;
  isFlagged: boolean;
  adjacent: number;
}

function createBoard(): Cell[][] {
  const board: Cell[][] = Array.from({ length: ROWS }, () =>
    Array.from({ length: COLS }, () => ({
      isMine: false,
      isRevealed: false,
      isFlagged: false,
      adjacent: 0,
    }))
  );
  let mines = 0;
  while (mines < MINES) {
    const r = Math.floor(Math.random() * ROWS);
    const c = Math.floor(Math.random() * COLS);
    if (!board[r][c].isMine) {
      board[r][c].isMine = true;
      mines++;
    }
  }
  for (let r = 0; r < ROWS; r++) {
    for (let c = 0; c < COLS; c++) {
      if (board[r][c].isMine) continue;
      let count = 0;
      for (let dr = -1; dr <= 1; dr++)
        for (let dc = -1; dc <= 1; dc++) {
          const nr = r + dr,
            nc = c + dc;
          if (nr >= 0 && nr < ROWS && nc >= 0 && nc < COLS && board[nr][nc].isMine) count++;
        }
      board[r][c].adjacent = count;
    }
  }
  return board;
}

export default function Minesweeper() {
  const [board, setBoard] = useState<Cell[][]>(createBoard);
  const [gameState, setGameState] = useState<'playing' | 'won' | 'lost'>('playing');
  const [flags, setFlags] = useState(0);

  const reveal = useCallback((r: number, c: number, b: Cell[][]): Cell[][] => {
    if (r < 0 || r >= ROWS || c < 0 || c >= COLS || b[r][c].isRevealed || b[r][c].isFlagged)
      return b;
    const nb = b.map((row) => row.map((cell) => ({ ...cell })));
    nb[r][c].isRevealed = true;
    if (nb[r][c].adjacent === 0 && !nb[r][c].isMine) {
      for (let dr = -1; dr <= 1; dr++) for (let dc = -1; dc <= 1; dc++) reveal(r + dr, c + dc, nb);
    }
    return nb;
  }, []);

  const handleClick = (r: number, c: number) => {
    if (gameState !== 'playing' || board[r][c].isRevealed || board[r][c].isFlagged) return;
    if (board[r][c].isMine) {
      const nb = board.map((row) => row.map((cell) => ({ ...cell, isRevealed: true })));
      setBoard(nb);
      setGameState('lost');
      return;
    }
    const nb = reveal(r, c, board);
    setBoard(nb);
    if (nb.every((row) => row.every((c) => c.isMine || c.isRevealed))) setGameState('won');
  };

  const handleRightClick = (e: React.MouseEvent, r: number, c: number) => {
    e.preventDefault();
    if (gameState !== 'playing' || board[r][c].isRevealed) return;
    const nb = board.map((row) => row.map((cell) => ({ ...cell })));
    nb[r][c].isFlagged = !nb[r][c].isFlagged;
    setBoard(nb);
    setFlags(nb.flat().filter((c) => c.isFlagged).length);
  };

  const reset = () => {
    setBoard(createBoard());
    setGameState('playing');
    setFlags(0);
  };

  const numberColors = [
    '',
    '#3b82f6',
    '#22c55e',
    '#ef4444',
    '#8b5cf6',
    '#f59e0b',
    '#06b6d4',
    '#1f2937',
    '#6b7280',
  ];

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 items-center justify-center p-4">
      <div className="flex items-center justify-between w-full max-w-[320px] mb-3">
        <div className="text-sm">💣 {MINES - flags}</div>
        <button onClick={reset} className="p-1.5 rounded-lg hover:bg-blue-500/20 transition-colors">
          <RotateCcw size={16} />
        </button>
        <div
          className={`text-sm font-medium ${gameState === 'won' ? 'text-green-400' : gameState === 'lost' ? 'text-red-400' : 'text-blue-300'}`}
        >
          {gameState === 'playing' ? '😊' : gameState === 'won' ? '🎉' : '💥'}
        </div>
      </div>
      <div
        className="bg-[#0a1420] rounded-xl border border-blue-500/15 p-2 inline-grid gap-[2px]"
        style={{ gridTemplateColumns: `repeat(${COLS}, 26px)` }}
      >
        {board.map((row, r) =>
          row.map((cell, c) => (
            <button
              key={`${r}-${c}`}
              onClick={() => handleClick(r, c)}
              onContextMenu={(e) => handleRightClick(e, r, c)}
              className={`w-[26px] h-[26px] rounded flex items-center justify-center text-xs font-bold transition-all ${
                cell.isRevealed ? 'bg-[#162032]' : 'bg-[#1e3350] hover:bg-[#254060] cursor-pointer'
              }`}
            >
              {cell.isFlagged && !cell.isRevealed && <Flag size={12} className="text-red-400" />}
              {cell.isRevealed && cell.isMine && <Bomb size={12} className="text-red-500" />}
              {cell.isRevealed && !cell.isMine && cell.adjacent > 0 && (
                <span style={{ color: numberColors[cell.adjacent] }}>{cell.adjacent}</span>
              )}
            </button>
          ))
        )}
      </div>
      <p className="text-[10px] text-blue-300/30 mt-2">Right-click to flag mines</p>
    </div>
  );
}
