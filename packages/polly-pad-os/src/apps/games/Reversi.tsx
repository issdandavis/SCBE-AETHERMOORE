import React, { useState } from 'react';
import { RotateCcw } from 'lucide-react';

const SIZE = 8;
const DIRS = [
  [-1, -1],
  [-1, 0],
  [-1, 1],
  [0, -1],
  [0, 1],
  [1, -1],
  [1, 0],
  [1, 1],
];

function createBoard(): (0 | 1 | 2)[][] {
  const b = Array.from({ length: SIZE }, () => Array(SIZE).fill(0) as (0 | 1 | 2)[]);
  b[3][3] = b[4][4] = 1;
  b[3][4] = b[4][3] = 2;
  return b;
}

function validMoves(board: (0 | 1 | 2)[][], player: 1 | 2): [number, number][] {
  const moves: [number, number][] = [];
  for (let r = 0; r < SIZE; r++)
    for (let c = 0; c < SIZE; c++) {
      if (board[r][c] !== 0) continue;
      for (const [dr, dc] of DIRS) {
        let nr = r + dr,
          nc = c + dc;
        let hasOpponent = false;
        while (nr >= 0 && nr < SIZE && nc >= 0 && nc < SIZE && board[nr][nc] === 3 - player) {
          hasOpponent = true;
          nr += dr;
          nc += dc;
        }
        if (
          hasOpponent &&
          nr >= 0 &&
          nr < SIZE &&
          nc >= 0 &&
          nc < SIZE &&
          board[nr][nc] === player
        ) {
          moves.push([r, c]);
          break;
        }
      }
    }
  return moves;
}

function makeMove(board: (0 | 1 | 2)[][], r: number, c: number, player: 1 | 2): (0 | 1 | 2)[][] {
  const nb = board.map((row) => [...row]);
  nb[r][c] = player;
  for (const [dr, dc] of DIRS) {
    let nr = r + dr,
      nc = c + dc;
    const toFlip: [number, number][] = [];
    while (nr >= 0 && nr < SIZE && nc >= 0 && nc < SIZE && board[nr][nc] === 3 - player) {
      toFlip.push([nr, nc]);
      nr += dr;
      nc += dc;
    }
    if (
      toFlip.length > 0 &&
      nr >= 0 &&
      nr < SIZE &&
      nc >= 0 &&
      nc < SIZE &&
      board[nr][nc] === player
    ) {
      toFlip.forEach(([fr, fc]) => (nb[fr][fc] = player));
    }
  }
  return nb;
}

export default function Reversi() {
  const [board, setBoard] = useState(createBoard);
  const [current, setCurrent] = useState<1 | 2>(1);
  const moves = validMoves(board, current);

  const handleClick = (r: number, c: number) => {
    if (!moves.some(([mr, mc]) => mr === r && mc === c)) return;
    const nb = makeMove(board, r, c, current);
    setBoard(nb);
    const next = current === 1 ? 2 : 1;
    if (validMoves(nb, next).length > 0) setCurrent(next);
    else if (validMoves(nb, current).length > 0) setCurrent(current);
  };

  const count = (player: 1 | 2) => board.flat().filter((c) => c === player).length;
  const reset = () => {
    setBoard(createBoard());
    setCurrent(1);
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 items-center justify-center p-3">
      <div className="flex items-center justify-between w-full max-w-[340px] mb-2">
        <h2 className="text-sm text-blue-200 font-semibold">Reversi</h2>
        <button onClick={reset} className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/50">
          <RotateCcw size={14} />
        </button>
      </div>
      <div className="flex gap-4 mb-2 text-xs">
        <span className="text-blue-300/40">
          Black: <span className="text-blue-200">{count(1)}</span>
        </span>
        <span className="text-blue-300/40">{current === 1 ? "Black's turn" : "White's turn"}</span>
        <span className="text-blue-300/40">
          White: <span className="text-blue-200">{count(2)}</span>
        </span>
      </div>
      <div className="grid grid-cols-8 gap-[2px] bg-green-800/40 p-2 rounded-xl border border-blue-500/15">
        {board.map((row, r) =>
          row.map((cell, c) => {
            const isValid = moves.some(([mr, mc]) => mr === r && mc === c);
            return (
              <button
                key={`${r}-${c}`}
                onClick={() => handleClick(r, c)}
                className={`w-9 h-9 rounded-full flex items-center justify-center transition-all ${isValid ? 'ring-1 ring-green-400/30' : ''}`}
              >
                {cell === 1 && (
                  <div className="w-7 h-7 rounded-full bg-gray-900 border border-gray-700" />
                )}
                {cell === 2 && (
                  <div className="w-7 h-7 rounded-full bg-gray-100 border border-gray-300" />
                )}
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}
