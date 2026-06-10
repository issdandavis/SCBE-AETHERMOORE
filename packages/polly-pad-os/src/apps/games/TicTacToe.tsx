import React, { useState } from 'react';
import { RotateCcw, X, Circle } from 'lucide-react';

export default function TicTacToe() {
  const [board, setBoard] = useState(Array(9).fill(null));
  const [xIsNext, setXIsNext] = useState(true);
  const [scores, setScores] = useState({ X: 0, O: 0, draw: 0 });

  const winner = calculateWinner(board);
  const isDraw = !winner && board.every(Boolean);

  function calculateWinner(squares: (string | null)[]) {
    const lines = [
      [0, 1, 2],
      [3, 4, 5],
      [6, 7, 8],
      [0, 3, 6],
      [1, 4, 7],
      [2, 5, 8],
      [0, 4, 8],
      [2, 4, 6],
    ];
    for (const [a, b, c] of lines)
      if (squares[a] && squares[a] === squares[b] && squares[a] === squares[c]) return squares[a];
    return null;
  }

  const handleClick = (i: number) => {
    if (board[i] || winner || isDraw) return;
    const nb = [...board];
    nb[i] = xIsNext ? 'X' : 'O';
    setBoard(nb);
    setXIsNext(!xIsNext);
    const w = calculateWinner(nb);
    if (w) setScores((s) => ({ ...s, [w]: s[w as keyof typeof s] + 1 }));
    else if (nb.every(Boolean)) setScores((s) => ({ ...s, draw: s.draw + 1 }));
  };

  const reset = () => {
    setBoard(Array(9).fill(null));
    setXIsNext(true);
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 items-center justify-center p-4">
      <div className="flex items-center justify-between w-full max-w-[280px] mb-4">
        <div className="text-xs">
          <span className="text-blue-400">X: {scores.X}</span>{' '}
          <span className="text-blue-300/30 mx-2">|</span>{' '}
          <span className="text-purple-400">O: {scores.O}</span>
        </div>
        <button onClick={reset} className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/50">
          <RotateCcw size={14} />
        </button>
        <div className="text-xs text-blue-300/30">Draw: {scores.draw}</div>
      </div>
      <div className="mb-3 text-sm">
        {winner ? (
          <span className={winner === 'X' ? 'text-blue-400' : 'text-purple-400'}>
            {winner} Wins!
          </span>
        ) : isDraw ? (
          <span className="text-blue-300/50">Draw!</span>
        ) : (
          <span className="text-blue-300/50">{xIsNext ? 'X' : 'O'}'s turn</span>
        )}
      </div>
      <div className="grid grid-cols-3 gap-2">
        {board.map((cell, i) => (
          <button
            key={i}
            onClick={() => handleClick(i)}
            className="w-20 h-20 rounded-xl bg-[#162032] border border-blue-500/10 hover:border-blue-500/30 flex items-center justify-center transition-all hover:bg-[#1a2d45]"
          >
            {cell === 'X' && <X size={36} className="text-blue-400" strokeWidth={3} />}
            {cell === 'O' && <Circle size={32} className="text-purple-400" strokeWidth={3} />}
          </button>
        ))}
      </div>
      <div className="mt-4">
        <button
          onClick={() => setScores({ X: 0, O: 0, draw: 0 })}
          className="text-[10px] text-blue-300/30 hover:text-blue-200/60 transition-colors"
        >
          Reset Scores
        </button>
      </div>
    </div>
  );
}
