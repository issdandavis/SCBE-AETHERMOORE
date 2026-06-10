import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Play, RotateCcw } from 'lucide-react';

const CANVAS_W = 400;
const CANVAS_H = 520;
const GRAVITY = 0.35;
const JUMP = -6;
const PIPE_W = 50;
const PIPE_GAP = 130;

export default function FlappyBird() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [gameState, setGameState] = useState<'idle' | 'playing' | 'over'>('idle');
  const [score, setScore] = useState(0);
  const [highScore, setHighScore] = useState(() =>
    parseInt(localStorage.getItem('flappy_hs') || '0')
  );
  const gameRef = useRef({
    bird: { y: 200, vy: 0 },
    pipes: [] as { x: number; topH: number; passed: boolean }[],
    frame: 0,
  });
  const reqRef = useRef<number | null>(null);

  const startGame = () => {
    gameRef.current = { bird: { y: 200, vy: 0 }, pipes: [], frame: 0 };
    setScore(0);
    setGameState('playing');
  };

  const flap = useCallback(() => {
    if (gameState === 'playing') gameRef.current.bird.vy = JUMP;
  }, [gameState]);

  const draw = useCallback(() => {
    const cvs = canvasRef.current;
    if (!cvs) return;
    const ctx = cvs.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);
    const g = gameRef.current;
    // Pipes
    ctx.fillStyle = '#22c55e';
    g.pipes.forEach((p) => {
      ctx.fillRect(p.x, 0, PIPE_W, p.topH);
      ctx.fillRect(p.x, p.topH + PIPE_GAP, PIPE_W, CANVAS_H);
    });
    // Bird
    ctx.fillStyle = '#fbbf24';
    ctx.beginPath();
    ctx.arc(60, g.bird.y, 12, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#0d1926';
    ctx.beginPath();
    ctx.arc(64, g.bird.y - 3, 3, 0, Math.PI * 2);
    ctx.fill();
  }, []);

  useEffect(() => {
    if (gameState !== 'playing') return;
    const loop = () => {
      const g = gameRef.current;
      g.frame++;
      g.bird.vy += GRAVITY;
      g.bird.y += g.bird.vy;
      if (g.frame % 100 === 0) {
        const topH = 50 + Math.random() * (CANVAS_H - PIPE_GAP - 150);
        g.pipes.push({ x: CANVAS_W, topH, passed: false });
      }
      g.pipes.forEach((p) => {
        p.x -= 2;
        if (!p.passed && p.x + PIPE_W < 60) {
          p.passed = true;
          setScore((s) => s + 1);
        }
        if (
          p.x < 72 &&
          p.x + PIPE_W > 48 &&
          (g.bird.y - 12 < p.topH || g.bird.y + 12 > p.topH + PIPE_GAP)
        ) {
          setGameState('over');
          setScore((s) => {
            if (s > highScore) {
              setHighScore(s);
              localStorage.setItem('flappy_hs', String(s));
            }
            return s;
          });
        }
      });
      g.pipes = g.pipes.filter((p) => p.x > -PIPE_W);
      if (g.bird.y > CANVAS_H - 12 || g.bird.y < 0) {
        setGameState('over');
        setScore((s) => {
          if (s > highScore) {
            setHighScore(s);
            localStorage.setItem('flappy_hs', String(s));
          }
          return s;
        });
      }
      draw();
      reqRef.current = requestAnimationFrame(loop);
    };
    reqRef.current = requestAnimationFrame(loop);
    return () => {
      if (reqRef.current) cancelAnimationFrame(reqRef.current);
    };
  }, [gameState, draw, highScore]);

  useEffect(() => {
    const handle = (e: KeyboardEvent) => {
      if ((e.key === ' ' || e.key === 'ArrowUp') && gameState === 'playing') flap();
    };
    window.addEventListener('keydown', handle);
    return () => window.removeEventListener('keydown', handle);
  }, [gameState, flap]);

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 items-center justify-center p-3">
      <div className="flex items-center justify-between w-full max-w-[400px] mb-2">
        <div className="text-sm">{score}</div>
        <div className="text-xs text-blue-300/30">HI: {highScore}</div>
      </div>
      <div className="relative">
        <canvas
          ref={canvasRef}
          width={CANVAS_W}
          height={CANVAS_H}
          className="bg-[#0a1420] rounded-xl border border-blue-500/15"
        />
        {(gameState === 'idle' || gameState === 'over') && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#0a1420]/85 rounded-xl">
            <h2 className="text-xl text-blue-200 mb-1">
              {gameState === 'over' ? 'Game Over' : 'Flappy Bird'}
            </h2>
            {gameState === 'over' && (
              <p className="text-sm text-blue-300/50 mb-3">Score: {score}</p>
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
      <button
        onClick={flap}
        className="mt-3 px-6 py-2 rounded-lg bg-blue-500/15 text-blue-300 text-sm hover:bg-blue-500/25 transition-colors"
      >
        Flap (Space)
      </button>
    </div>
  );
}
