import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Play, RotateCcw } from 'lucide-react';

const CANVAS_W = 700;
const CANVAS_H = 200;
const DINO_SIZE = 40;
const GRAVITY = 0.6;
const JUMP_FORCE = -11;

export default function DinoRun() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [gameState, setGameState] = useState<'idle' | 'playing' | 'over'>('idle');
  const [score, setScore] = useState(0);
  const [highScore, setHighScore] = useState(() =>
    parseInt(localStorage.getItem('dino_hs') || '0')
  );
  const gameRef = useRef({
    dino: { y: CANVAS_H - DINO_SIZE - 10, vy: 0, grounded: true },
    obstacles: [] as { x: number; w: number; h: number; passed: boolean }[],
    speed: 6,
    frame: 0,
  });
  const reqRef = useRef<number | null>(null);

  const startGame = () => {
    gameRef.current = {
      dino: { y: CANVAS_H - DINO_SIZE - 10, vy: 0, grounded: true },
      obstacles: [],
      speed: 6,
      frame: 0,
    };
    setScore(0);
    setGameState('playing');
  };

  const jump = useCallback(() => {
    const g = gameRef.current;
    if (g.dino.grounded) {
      g.dino.vy = JUMP_FORCE;
      g.dino.grounded = false;
    }
  }, []);

  const draw = useCallback(() => {
    const cvs = canvasRef.current;
    if (!cvs) return;
    const ctx = cvs.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);
    // Ground
    ctx.strokeStyle = '#1e3a5f';
    ctx.beginPath();
    ctx.moveTo(0, CANVAS_H - 10);
    ctx.lineTo(CANVAS_W, CANVAS_H - 10);
    ctx.stroke();
    // Dino
    const g = gameRef.current;
    ctx.fillStyle = '#60a5fa';
    ctx.fillRect(50, g.dino.y, DINO_SIZE, DINO_SIZE);
    // Eye
    ctx.fillStyle = '#0d1926';
    ctx.fillRect(70, g.dino.y + 8, 6, 6);
    // Obstacles
    ctx.fillStyle = '#f87171';
    g.obstacles.forEach((o) => ctx.fillRect(o.x, CANVAS_H - 10 - o.h, o.w, o.h));
  }, []);

  useEffect(() => {
    if (gameState !== 'playing') return;
    const loop = () => {
      const g = gameRef.current;
      g.frame++;
      if (g.frame % 60 === 0) g.speed += 0.2;
      // Dino physics
      g.dino.vy += GRAVITY;
      g.dino.y += g.dino.vy;
      if (g.dino.y >= CANVAS_H - DINO_SIZE - 10) {
        g.dino.y = CANVAS_H - DINO_SIZE - 10;
        g.dino.vy = 0;
        g.dino.grounded = true;
      }
      // Obstacles
      if (g.frame % Math.max(40, 120 - Math.floor(g.speed * 5)) === 0) {
        const isBird = Math.random() > 0.7;
        g.obstacles.push({
          x: CANVAS_W,
          w: 20 + Math.random() * 15,
          h: isBird ? 25 : 35 + Math.random() * 20,
          passed: false,
        });
      }
      g.obstacles.forEach((o) => {
        o.x -= g.speed;
        if (!o.passed && o.x < 50) {
          o.passed = true;
          setScore((s) => s + 1);
        }
        // Collision
        if (o.x < 50 + DINO_SIZE && o.x + o.w > 50 && g.dino.y + DINO_SIZE > CANVAS_H - 10 - o.h) {
          setGameState('over');
          setScore((s) => {
            if (s > highScore) {
              setHighScore(s);
              localStorage.setItem('dino_hs', String(s));
            }
            return s;
          });
        }
      });
      g.obstacles = g.obstacles.filter((o) => o.x > -50);
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
      if ((e.key === ' ' || e.key === 'ArrowUp') && gameState === 'playing') {
        e.preventDefault();
        jump();
      }
    };
    window.addEventListener('keydown', handle);
    return () => window.removeEventListener('keydown', handle);
  }, [gameState, jump]);

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 items-center justify-center p-3">
      <div className="flex items-center justify-between w-full max-w-[700px] mb-2">
        <div className="text-xs text-blue-300/50">
          Score: <span className="text-blue-200">{score}</span>
        </div>
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
              {gameState === 'over' ? 'Game Over' : 'Dino Run'}
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
        onClick={jump}
        className="mt-3 px-6 py-2 rounded-lg bg-blue-500/15 text-blue-300 text-sm hover:bg-blue-500/25 transition-colors"
      >
        Jump (Space)
      </button>
    </div>
  );
}
