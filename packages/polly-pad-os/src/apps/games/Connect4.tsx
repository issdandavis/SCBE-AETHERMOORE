import React, { useState } from 'react';
import { RotateCcw } from 'lucide-react';

const ROWS = 6;
const COLS = 7;

function checkWin(board: (0 | 1 | 2)[][], r: number, c: number, player: 1 | 2): boolean {
  const dirs = [
    [0, 1],
    [1, 0],
    [1, 1],
    [1, -1],
  ];
  for (const [dr, dc] of dirs) {
    let count = 1;
    for (const sign of [1, -1]) {
      for (let i = 1; i < 4; i++) {
        const nr = r + dr * i * sign;
        const nc = c + dc * i * sign;
        if (nr >= 0 && nr < ROWS && nc >= 0 && nc < COLS && board[nr][nc] === player) count++;
        else break;
      }
    }
    if (count >= 4) return true;
  }
  return false;
}

export default function Connect4() {
  const [board, setBoard] = useState<(0 | 1 | 2)[][]>(() =>
    Array.from({ length: ROWS }, () => Array(COLS).fill(0))
  );
  const [current, setCurrent] = useState<1 | 2>(1);
  const [winner, setWinner] = useState<0 | 1 | 2>(0);

  const drop = (col: number) => {
    if (winner) return;
    const newBoard = board.map((r) => [...r]);
    for (let r = ROWS - 1; r >= 0; r--) {
      if (newBoard[r][col] === 0) {
        newBoard[r][col] = current;
        if (checkWin(newBoard, r, col, current)) setWinner(current);
        setBoard(newBoard);
        setCurrent(current === 1 ? 2 : 1);
        return;
      }
    }
  };

  const reset = () => {
    setBoard(Array.from({ length: ROWS }, () => Array(COLS).fill(0)));
    setCurrent(1);
    setWinner(0);
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 items-center justify-center p-3">
      <div className="flex items-center justify-between w-full max-w-[340px] mb-3">
        <h2 className="text-sm text-blue-200 font-semibold">Connect 4</h2>
        <button onClick={reset} className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/50">
          <RotateCcw size={14} />
        </button>
      </div>
      {!winner && (
        <div className="text-xs text-blue-300/40 mb-2">
          Player {current === 1 ? 'Red' : 'Yellow'}'s turn
        </div>
      )}
      {winner && (
        <div className="text-sm text-green-400 mb-2">
          Player {winner === 1 ? 'Red' : 'Yellow'} wins!
        </div>
      )}
      <div
        className="bg-[#0a1420] rounded-xl border border-blue-500/15 p-2 inline-grid gap-1"
        style={{ gridTemplateColumns: `repeat(${COLS}, 36px)` }}
      >
        {board.map((row, r) =>
          row.map((cell, c) => (
            <button
              key={`${r}-${c}`}
              onClick={() => drop(c)}
              className="w-9 h-9 rounded-full border-2 border-blue-500/10 transition-all hover:border-blue-500/30"
              style={{
                background: cell === 0 ? '#162032' : cell === 1 ? '#ef4444' : '#fbbf24',
                boxShadow: cell !== 0 ? `0 0 8px ${cell === 1 ? '#ef4444' : '#fbbf24'}40` : 'none',
              }}
            />
          ))
        )}
      </div>
    </div>
  );
}
