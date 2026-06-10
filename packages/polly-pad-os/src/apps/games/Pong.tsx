import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Play, RotateCcw } from 'lucide-react';

const CANVAS_W = 640;
const CANVAS_H = 400;
const PADDLE_H = 80;
const PADDLE_W = 12;
const BALL_SIZE = 10;

export default function Pong() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [gameState, setGameState] = useState<'idle' | 'playing' | 'over'>('idle');
  const [score, setScore] = useState({ p: 0, ai: 0 });
  const [winner, setWinner] = useState('');
  const gameRef = useRef({
    ball: { x: CANVAS_W / 2, y: CANVAS_H / 2, dx: 4, dy: 3 },
    pPaddle: CANVAS_H / 2 - PADDLE_H / 2,
    aiPaddle: CANVAS_H / 2 - PADDLE_H / 2,
  });
  const keysRef = useRef({ up: false, down: false });
  const reqRef = useRef<number | null>(null);

  const draw = useCallback(() => {
    const cvs = canvasRef.current;
    if (!cvs) return;
    const ctx = cvs.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);
    ctx.fillStyle = '#1e3a5f';
    ctx.fillRect(CANVAS_W / 2 - 1, 0, 2, CANVAS_H);
    const g = gameRef.current;
    ctx.fillStyle = '#60a5fa';
    ctx.fillRect(20, g.pPaddle, PADDLE_W, PADDLE_H);
    ctx.fillStyle = '#f87171';
    ctx.fillRect(CANVAS_W - 20 - PADDLE_W, g.aiPaddle, PADDLE_W, PADDLE_H);
    ctx.fillStyle = '#93bbfc';
    ctx.beginPath();
    ctx.arc(g.ball.x, g.ball.y, BALL_SIZE / 2, 0, Math.PI * 2);
    ctx.fill();
  }, []);

  const startGame = () => {
    gameRef.current = {
      ball: { x: CANVAS_W / 2, y: CANVAS_H / 2, dx: 4, dy: 3 },
      pPaddle: CANVAS_H / 2 - PADDLE_H / 2,
      aiPaddle: CANVAS_H / 2 - PADDLE_H / 2,
    };
    setScore({ p: 0, ai: 0 });
    setGameState('playing');
  };

  useEffect(() => {
    if (gameState !== 'playing') return;
    const loop = () => {
      const g = gameRef.current;
      g.ball.x += g.ball.dx;
      g.ball.y += g.ball.dy;
      if (g.ball.y <= 0 || g.ball.y >= CANVAS_H) g.ball.dy *= -1;
      if (keysRef.current.up) g.pPaddle = Math.max(0, g.pPaddle - 5);
      if (keysRef.current.down) g.pPaddle = Math.min(CANVAS_H - PADDLE_H, g.pPaddle + 5);
      const aiCenter = g.aiPaddle + PADDLE_H / 2;
      if (aiCenter < g.ball.y - 10) g.aiPaddle = Math.min(CANVAS_H - PADDLE_H, g.aiPaddle + 3.5);
      else if (aiCenter > g.ball.y + 10) g.aiPaddle = Math.max(0, g.aiPaddle - 3.5);
      if (g.ball.x <= 20 + PADDLE_W && g.ball.y >= g.pPaddle && g.ball.y <= g.pPaddle + PADDLE_H)
        g.ball.dx = Math.abs(g.ball.dx) * 1.05;
      if (
        g.ball.x >= CANVAS_W - 20 - PADDLE_W &&
        g.ball.y >= g.aiPaddle &&
        g.ball.y <= g.aiPaddle + PADDLE_H
      )
        g.ball.dx = -Math.abs(g.ball.dx) * 1.05;
      if (g.ball.x < 0) {
        setScore((s) => {
          const ns = { ...s, ai: s.ai + 1 };
          if (ns.ai >= 5) {
            setGameState('over');
            setWinner('AI');
          }
          return ns;
        });
        g.ball.x = CANVAS_W / 2;
        g.ball.dx = -4;
      }
      if (g.ball.x > CANVAS_W) {
        setScore((s) => {
          const ns = { ...s, p: s.p + 1 };
          if (ns.p >= 5) {
            setGameState('over');
            setWinner('You');
          }
          return ns;
        });
        g.ball.x = CANVAS_W / 2;
        g.ball.dx = 4;
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
      if (e.key === 'ArrowUp') keysRef.current.up = e.type === 'keydown';
      if (e.key === 'ArrowDown') keysRef.current.down = e.type === 'keydown';
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
      <div className="flex items-center justify-between w-full max-w-[640px] mb-2">
        <div className="text-sm text-blue-400">Player: {score.p}</div>
        <div className="text-lg font-bold text-blue-200">PONG</div>
        <div className="text-sm text-red-400">AI: {score.ai}</div>
      </div>
      <div className="relative">
        <canvas
          ref={canvasRef}
          width={CANVAS_W}
          height={CANVAS_H}
          className="bg-[#0a1420] rounded-xl border border-blue-500/15"
          style={{ maxWidth: '100%', height: 'auto' }}
        />
        {(gameState === 'idle' || gameState === 'over') && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#0a1420]/85 rounded-xl">
            <h2 className="text-xl text-blue-200 mb-2">
              {gameState === 'over' ? `${winner} Win!` : 'Pong'}
            </h2>
            {gameState === 'over' && (
              <p className="text-sm text-blue-300/50 mb-3">
                {score.p} - {score.ai}
              </p>
            )}
            <button
              onClick={startGame}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-500/20 hover:bg-blue-500/30 text-blue-200 text-sm"
            >
              <Play size={16} /> {gameState === 'over' ? 'Retry' : 'Start'}
            </button>
          </div>
        )}
      </div>
      <div className="flex gap-2 mt-2">
        <button
          onMouseDown={() => (keysRef.current.up = true)}
          onMouseUp={() => (keysRef.current.up = false)}
          onTouchStart={() => (keysRef.current.up = true)}
          onTouchEnd={() => (keysRef.current.up = false)}
          className="px-4 py-2 rounded bg-blue-500/10 text-blue-300 text-xs"
        >
          ▲ Up
        </button>
        <button
          onMouseDown={() => (keysRef.current.down = true)}
          onMouseUp={() => (keysRef.current.down = false)}
          onTouchStart={() => (keysRef.current.down = true)}
          onTouchEnd={() => (keysRef.current.down = false)}
          className="px-4 py-2 rounded bg-blue-500/10 text-blue-300 text-xs"
        >
          ▼ Down
        </button>
      </div>
    </div>
  );
}
