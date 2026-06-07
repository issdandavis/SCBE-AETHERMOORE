import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Play, RotateCcw, Trophy } from 'lucide-react';

const COLS = 10;
const ROWS = 20;
const SHAPES = [
  { shape: [[1, 1, 1, 1]], color: '#60a5fa' },
  {
    shape: [
      [1, 1],
      [1, 1],
    ],
    color: '#fbbf24',
  },
  {
    shape: [
      [0, 1, 0],
      [1, 1, 1],
    ],
    color: '#a78bfa',
  },
  {
    shape: [
      [1, 0, 0],
      [1, 1, 1],
    ],
    color: '#f87171',
  },
  {
    shape: [
      [0, 0, 1],
      [1, 1, 1],
    ],
    color: '#4ade80',
  },
  {
    shape: [
      [1, 1, 0],
      [0, 1, 1],
    ],
    color: '#fb923c',
  },
  {
    shape: [
      [0, 1, 1],
      [1, 1, 0],
    ],
    color: '#f472b6',
  },
];

function createBoard() {
  return Array.from({ length: ROWS }, () => Array(COLS).fill(0));
}

function randomPiece() {
  const t = SHAPES[Math.floor(Math.random() * SHAPES.length)];
  return { shape: t.shape.map((r) => [...r]), color: t.color, x: 3, y: 0 };
}

export default function Tetris() {
  const [board, setBoard] = useState(createBoard());
  const [piece, setPiece] = useState(randomPiece);
  const [gameState, setGameState] = useState<'idle' | 'playing' | 'over'>('idle');
  const [score, setScore] = useState(0);
  const [lines, setLines] = useState(0);
  const [level, setLevel] = useState(1);
  const [highScore, setHighScore] = useState(() =>
    parseInt(localStorage.getItem('tetris_hs') || '0')
  );
  const gameLoopRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);
  const speedRef = useRef(800);

  const isValid = useCallback(
    (shape: number[][], x: number, y: number, b: (number | string)[][]) => {
      for (let r = 0; r < shape.length; r++) {
        for (let c = 0; c < shape[r].length; c++) {
          if (shape[r][c]) {
            const nx = x + c,
              ny = y + r;
            if (nx < 0 || nx >= COLS || ny >= ROWS) return false;
            if (ny >= 0 && b[ny][nx]) return false;
          }
        }
      }
      return true;
    },
    []
  );

  const mergePiece = useCallback((b: (number | string)[][], p: typeof piece) => {
    const nb = b.map((r) => [...r]);
    for (let r = 0; r < p.shape.length; r++) {
      for (let c = 0; c < p.shape[r].length; c++) {
        if (p.shape[r][c] && p.y + r >= 0) nb[p.y + r][p.x + c] = p.color;
      }
    }
    return nb;
  }, []);

  const clearLines = useCallback((b: (number | string)[][]) => {
    const nb = b.filter((r) => !r.every((c) => c !== 0));
    const cleared = ROWS - nb.length;
    while (nb.length < ROWS) nb.unshift(Array(COLS).fill(0));
    return { board: nb, cleared };
  }, []);

  const rotate = useCallback((shape: number[][]) => {
    const rows = shape.length,
      cols = shape[0].length;
    const rotated: number[][] = Array.from({ length: cols }, () => Array(rows).fill(0));
    for (let r = 0; r < rows; r++)
      for (let c = 0; c < cols; c++) rotated[c][rows - 1 - r] = shape[r][c];
    return rotated;
  }, []);

  const startGame = () => {
    const b = createBoard();
    setBoard(b);
    setPiece(randomPiece());
    setScore(0);
    setLines(0);
    setLevel(1);
    speedRef.current = 800;
    setGameState('playing');
  };

  useEffect(() => {
    if (gameState !== 'playing') return;
    gameLoopRef.current = setInterval(() => {
      setPiece((p) => {
        setBoard((b) => {
          if (isValid(p.shape, p.x, p.y + 1, b)) return b;
          const nb = mergePiece(b, p);
          const { board: cb, cleared } = clearLines(nb);
          if (cleared > 0) {
            setLines((l) => {
              const nl = l + cleared;
              const newLevel = Math.floor(nl / 10) + 1;
              setLevel(newLevel);
              speedRef.current = Math.max(100, 800 - Math.floor(nl / 10) * 60);
              setScore((s) => {
                const ns = s + cleared * 100 * newLevel;
                if (ns > highScore) {
                  setHighScore(ns);
                  localStorage.setItem('tetris_hs', String(ns));
                }
                return ns;
              });
              return nl;
            });
          }
          const np = randomPiece();
          if (!isValid(np.shape, np.x, np.y, cb)) {
            setGameState('over');
            return cb;
          }
          setPiece(np);
          return cb;
        });
        return p;
      });
    }, speedRef.current);
    return () => clearInterval(gameLoopRef.current);
  }, [gameState, isValid, mergePiece, clearLines, highScore]);

  const move = (dx: number) =>
    setPiece((p) => (isValid(p.shape, p.x + dx, p.y, board) ? { ...p, x: p.x + dx } : p));
  const drop = () =>
    setPiece((p) => (isValid(p.shape, p.x, p.y + 1, board) ? { ...p, y: p.y + 1 } : p));
  const rot = () =>
    setPiece((p) => {
      const r = rotate(p.shape);
      return isValid(r, p.x, p.y, board) ? { ...p, shape: r } : p;
    });

  useEffect(() => {
    const handle = (e: KeyboardEvent) => {
      if (gameState !== 'playing') return;
      switch (e.key) {
        case 'ArrowLeft':
          move(-1);
          break;
        case 'ArrowRight':
          move(1);
          break;
        case 'ArrowDown':
          drop();
          break;
        case 'ArrowUp':
        case ' ':
          rot();
          break;
      }
    };
    window.addEventListener('keydown', handle);
    return () => window.removeEventListener('keydown', handle);
  }, [gameState, board]);

  const displayBoard = board.map((r) => [...r]);
  if (gameState === 'playing') {
    for (let r = 0; r < piece.shape.length; r++) {
      for (let c = 0; c < piece.shape[r].length; c++) {
        if (piece.shape[r][c] && piece.y + r >= 0)
          displayBoard[piece.y + r][piece.x + c] = piece.color;
      }
    }
  }

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 items-center justify-center p-3">
      <div className="flex items-center justify-between w-full max-w-[300px] mb-2">
        <div className="text-xs text-blue-300/50">
          Score: <span className="text-blue-200">{score}</span>
        </div>
        <div className="text-xs text-blue-300/50">
          Level: <span className="text-blue-200">{level}</span>
        </div>
        <div className="flex items-center gap-1 text-xs text-blue-300/30">
          <Trophy size={12} />
          {highScore}
        </div>
      </div>
      <div className="relative bg-[#0a1420] rounded-xl border border-blue-500/15 p-1">
        {(gameState === 'idle' || gameState === 'over') && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#0a1420]/90 z-10 rounded-xl">
            <h2 className="text-lg text-blue-200 mb-1">
              {gameState === 'over' ? 'Game Over' : 'Tetris'}
            </h2>
            {gameState === 'over' && <p className="text-sm text-blue-200 mb-1">Score: {score}</p>}
            <button
              onClick={startGame}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-500/20 hover:bg-blue-500/30 text-blue-200 text-sm transition-colors"
            >
              <Play size={16} /> {gameState === 'over' ? 'Retry' : 'Start'}
            </button>
          </div>
        )}
        <div style={{ display: 'grid', gridTemplateColumns: `repeat(${COLS}, 16px)`, gap: '1px' }}>
          {displayBoard.flat().map((cell, i) => (
            <div
              key={i}
              style={{
                width: 16,
                height: 16,
                borderRadius: 2,
                background: cell || '#132744',
                boxShadow: cell ? `0 0 4px ${cell}40` : 'none',
              }}
            />
          ))}
        </div>
      </div>
      <div className="mt-2 flex gap-1">
        <button
          onClick={() => move(-1)}
          className="px-3 py-1.5 rounded bg-blue-500/10 text-blue-300 text-xs hover:bg-blue-500/20"
        >
          ←
        </button>
        <button
          onClick={rot}
          className="px-3 py-1.5 rounded bg-blue-500/10 text-blue-300 text-xs hover:bg-blue-500/20"
        >
          ↻
        </button>
        <button
          onClick={drop}
          className="px-3 py-1.5 rounded bg-blue-500/10 text-blue-300 text-xs hover:bg-blue-500/20"
        >
          ↓
        </button>
        <button
          onClick={() => move(1)}
          className="px-3 py-1.5 rounded bg-blue-500/10 text-blue-300 text-xs hover:bg-blue-500/20"
        >
          →
        </button>
      </div>
    </div>
  );
}
