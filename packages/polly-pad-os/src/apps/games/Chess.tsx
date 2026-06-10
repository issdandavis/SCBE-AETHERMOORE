import React, { useState } from 'react';
import { RotateCcw } from 'lucide-react';

const PIECES: Record<string, string> = {
  K: '♔',
  Q: '♕',
  R: '♖',
  B: '♗',
  N: '♘',
  P: '♙',
  k: '♚',
  q: '♛',
  r: '♜',
  b: '♝',
  n: '♞',
  p: '♟',
};

const INITIAL_BOARD = [
  ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],
  ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],
  ['', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', ''],
  ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],
  ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R'],
];

export default function Chess() {
  const [board, setBoard] = useState(() => INITIAL_BOARD.map((r) => [...r]));
  const [selected, setSelected] = useState<{ r: number; c: number } | null>(null);
  const [turn, setTurn] = useState<'white' | 'black'>('white');
  const [moves, setMoves] = useState<{ from: [number, number]; to: [number, number] }[]>([]);
  const [captured, setCaptured] = useState<string[]>([]);

  const isValidMove = (fr: number, fc: number, tr: number, tc: number, b: string[][]) => {
    const piece = b[fr][fc];
    if (!piece) return false;
    const isWhite = piece === piece.toUpperCase();
    if (turn === 'white' && !isWhite) return false;
    if (turn === 'black' && isWhite) return false;
    const target = b[tr][tc];
    if (target && isWhite === (target === target.toUpperCase())) return false;
    const dr = tr - fr,
      dc = tc - fc;
    switch (piece.toLowerCase()) {
      case 'p': {
        const dir = isWhite ? -1 : 1;
        const startRow = isWhite ? 6 : 1;
        if (dc === 0 && !target) {
          if (dr === dir) return true;
          if (fr === startRow && dr === 2 * dir && !b[fr + dir][fc]) return true;
        }
        if (Math.abs(dc) === 1 && dr === dir && target) return true;
        return false;
      }
      case 'r':
        return (dr === 0 || dc === 0) && !isBlocked(fr, fc, tr, tc, b);
      case 'b':
        return Math.abs(dr) === Math.abs(dc) && !isBlocked(fr, fc, tr, tc, b);
      case 'q':
        return (
          (dr === 0 || dc === 0 || Math.abs(dr) === Math.abs(dc)) && !isBlocked(fr, fc, tr, tc, b)
        );
      case 'n':
        return (
          (Math.abs(dr) === 2 && Math.abs(dc) === 1) || (Math.abs(dr) === 1 && Math.abs(dc) === 2)
        );
      case 'k':
        return Math.abs(dr) <= 1 && Math.abs(dc) <= 1;
      default:
        return false;
    }
  };

  const isBlocked = (fr: number, fc: number, tr: number, tc: number, b: string[][]) => {
    const dr = tr - fr === 0 ? 0 : (tr - fr) / Math.abs(tr - fr);
    const dc = tc - fc === 0 ? 0 : (tc - fc) / Math.abs(tc - fc);
    let r = fr + dr,
      c = fc + dc;
    while (r !== tr || c !== tc) {
      if (b[r][c]) return true;
      r += dr;
      c += dc;
    }
    return false;
  };

  const handleCellClick = (r: number, c: number) => {
    if (selected) {
      if (selected.r === r && selected.c === c) {
        setSelected(null);
        return;
      }
      if (isValidMove(selected.r, selected.c, r, c, board)) {
        const newBoard = board.map((row) => [...row]);
        const capturedPiece = newBoard[r][c];
        if (capturedPiece) setCaptured((prev) => [...prev, capturedPiece]);
        newBoard[r][c] = newBoard[selected.r][selected.c];
        newBoard[selected.r][selected.c] = '';
        // Promotion
        if (newBoard[r][c] === 'P' && r === 0) newBoard[r][c] = 'Q';
        if (newBoard[r][c] === 'p' && r === 7) newBoard[r][c] = 'q';
        setBoard(newBoard);
        setMoves((prev) => [...prev, { from: [selected.r, selected.c], to: [r, c] }]);
        setTurn((t) => (t === 'white' ? 'black' : 'white'));
        setSelected(null);
        return;
      }
    }
    if (board[r][c]) {
      const isWhite = board[r][c] === board[r][c].toUpperCase();
      if ((turn === 'white' && isWhite) || (turn === 'black' && !isWhite)) setSelected({ r, c });
    }
  };

  const reset = () => {
    setBoard(INITIAL_BOARD.map((r) => [...r]));
    setSelected(null);
    setTurn('white');
    setMoves([]);
    setCaptured([]);
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 items-center justify-center p-2">
      <div className="flex items-center justify-between w-full max-w-[360px] mb-2">
        <div className="text-xs text-blue-300/50">
          {turn === 'white' ? 'White' : 'Black'}'s turn
        </div>
        <button onClick={reset} className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/50">
          <RotateCcw size={14} />
        </button>
      </div>
      <div className="grid grid-cols-8 border-2 border-blue-500/20 rounded-lg overflow-hidden">
        {board.map((row, r) =>
          row.map((cell, c) => {
            const isDark = (r + c) % 2 === 1;
            const isSelected = selected?.r === r && selected?.c === c;
            const isValidDest = selected && isValidMove(selected.r, selected.c, r, c, board);
            return (
              <button
                key={`${r}-${c}`}
                onClick={() => handleCellClick(r, c)}
                className={`w-10 h-10 flex items-center justify-center text-xl transition-all ${
                  isDark ? 'bg-[#1a3a5c]' : 'bg-[#0d1f35]'
                } ${isSelected ? 'ring-2 ring-yellow-400/50' : ''} ${isValidDest ? 'ring-1 ring-green-400/30' : ''}`}
              >
                {cell && (
                  <span
                    style={{
                      color: cell === cell.toUpperCase() ? '#e2e8f0' : '#94a3b8',
                      textShadow: '0 1px 2px rgba(0,0,0,0.5)',
                    }}
                  >
                    {PIECES[cell]}
                  </span>
                )}
              </button>
            );
          })
        )}
      </div>
      {captured.length > 0 && (
        <div className="mt-2 text-xs text-blue-300/40 flex gap-1 flex-wrap max-w-[360px]">
          Captured:{' '}
          {captured.map((p, i) => (
            <span key={i}>{PIECES[p]}</span>
          ))}
        </div>
      )}
    </div>
  );
}
