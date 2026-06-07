import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Play, RotateCcw } from 'lucide-react';

const W = 52;
const H = 32;

export default function Breakout() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [gameState, setGameState] = useState<'idle' | 'playing' | 'over' | 'won'>('idle');
  const [score, setScore] = useState(0);
  const [lives, setLives] = useState(3);
  const [level, setLevel] = useState(1);
  const gameRef = useRef({
    ball: { x: 26, y: 20, dx: 0.6, dy: -0.6 },
    paddle: 22,
    bricks: [] as { x: number; y: number; active: boolean }[],
  });
  const keysRef = useRef({ left: false, right: false });
  const reqRef = useRef<number | null>(null);

  const initBricks = useCallback((lvl: number) => {
    const bricks: { x: number; y: number; active: boolean }[] = [];
    const rows = 3 + lvl;
    for (let r = 2; r < rows + 2; r++)
      for (let c = 1; c < W - 1; c++) if (c % 2 === 0) bricks.push({ x: c, y: r, active: true });
    return bricks;
  }, []);

  const startGame = () => {
    const bricks = initBricks(level);
    gameRef.current = {
      ball: { x: 26, y: 20, dx: 0.5 + level * 0.05, dy: -(0.5 + level * 0.05) },
      paddle: 22,
      bricks,
    };
    setScore(0);
    setLives(3);
    setGameState('playing');
  };

  const draw = useCallback(() => {
    const cvs = canvasRef.current;
    if (!cvs) return;
    const ctx = cvs.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, W * 10, H * 10);
    const g = gameRef.current;
    g.bricks.forEach((b) => {
      if (b.active) {
        ctx.fillStyle = `hsl(${b.y * 30}, 60%, 50%)`;
        ctx.fillRect(b.x * 10, b.y * 10, 8, 8);
      }
    });
    ctx.fillStyle = '#60a5fa';
    ctx.fillRect(g.paddle * 10, (H - 2) * 10, 8 * 10, 8);
    ctx.fillStyle = '#93bbfc';
    ctx.beginPath();
    ctx.arc(g.ball.x * 10, g.ball.y * 10, 5, 0, Math.PI * 2);
    ctx.fill();
  }, []);

  useEffect(() => {
    if (gameState !== 'playing') return;
    const loop = () => {
      const g = gameRef.current;
      g.ball.x += g.ball.dx;
      g.ball.y += g.ball.dy;
      if (g.ball.x <= 0.5 || g.ball.x >= W - 0.5) g.ball.dx *= -1;
      if (g.ball.y <= 0.5) g.ball.dy = Math.abs(g.ball.dy);
      if (g.ball.y >= H - 2 && g.ball.x >= g.paddle && g.ball.x <= g.paddle + 8) {
        g.ball.dy = -Math.abs(g.ball.dy);
        g.ball.dx += (Math.random() - 0.5) * 0.2;
      }
      if (g.ball.y > H) {
        setLives((l) => {
          if (l <= 1) {
            setGameState('over');
            return 0;
          }
          g.ball.x = 26;
          g.ball.y = 20;
          g.ball.dy = -Math.abs(g.ball.dy);
          return l - 1;
        });
      }
      if (keysRef.current.left) g.paddle = Math.max(0, g.paddle - 0.8);
      if (keysRef.current.right) g.paddle = Math.min(W - 8, g.paddle + 0.8);
      g.bricks.forEach((b) => {
        if (b.active && Math.abs(g.ball.x - b.x) < 1 && Math.abs(g.ball.y - b.y) < 1) {
          b.active = false;
          g.ball.dy *= -1;
          setScore((s) => s + 10);
        }
      });
      if (g.bricks.every((b) => !b.active)) {
        setGameState('won');
        setLevel((l) => l + 1);
      }
      draw();
      reqRef.current = requestAnimationFrame(loop);
    };
    reqRef.current = requestAnimationFrame(loop);
    return () => {
      if (reqRef.current) cancelAnimationFrame(reqRef.current);
    };
  }, [gameState, draw]);

  useEffect(() => {
    const handle = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') keysRef.current.left = e.type === 'keydown';
      if (e.key === 'ArrowRight') keysRef.current.right = e.type === 'keydown';
    };
    window.addEventListener('keydown', handle);
    window.addEventListener('keyup', handle);
    return () => {
      window.removeEventListener('keydown', handle);
      window.removeEventListener('keyup', handle);
    };
  }, []);

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 items-center justify-center p-3">
      <div className="flex items-center justify-between w-full max-w-[520px] mb-2">
        <div className="text-xs text-blue-300/50">
          Score: <span className="text-blue-200">{score}</span>
        </div>
        <div className="text-xs text-blue-300/50">
          Lives: <span className="text-blue-200">{lives}</span>
        </div>
        <div className="text-xs text-blue-300/50">
          Level: <span className="text-blue-200">{level}</span>
        </div>
      </div>
      <div className="relative">
        <canvas
          ref={canvasRef}
          width={W * 10}
          height={H * 10}
          className="bg-[#0a1420] rounded-xl border border-blue-500/15"
        />
        {gameState !== 'playing' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#0a1420]/85 rounded-xl">
            <h2 className="text-xl text-blue-200 mb-2">
              {gameState === 'idle'
                ? 'Breakout'
                : gameState === 'won'
                  ? 'Level Complete!'
                  : 'Game Over'}
            </h2>
            {gameState === 'over' && (
              <p className="text-sm text-blue-300/50 mb-3">Score: {score}</p>
            )}
            <button
              onClick={startGame}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-500/20 hover:bg-blue-500/30 text-blue-200 text-sm"
            >
              <Play size={16} /> Start
            </button>
          </div>
        )}
      </div>
      <div className="flex gap-2 mt-2">
        <button
          onMouseDown={() => (keysRef.current.left = true)}
          onMouseUp={() => (keysRef.current.left = false)}
          className="px-4 py-2 rounded bg-blue-500/10 text-blue-300 text-xs"
        >
          ← Left
        </button>
        <button
          onMouseDown={() => (keysRef.current.right = true)}
          onMouseUp={() => (keysRef.current.right = false)}
          className="px-4 py-2 rounded bg-blue-500/10 text-blue-300 text-xs"
        >
          Right →
        </button>
      </div>
    </div>
  );
}
