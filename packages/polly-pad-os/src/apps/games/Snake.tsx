import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Play, RotateCcw, Trophy } from 'lucide-react';

const GRID_W = 25;
const GRID_H = 21;
const INITIAL_SPEED = 150;

export default function Snake() {
  const [snake, setSnake] = useState([{ x: 12, y: 10 }]);
  const [food, setFood] = useState({ x: 15, y: 10 });
  const [dir, setDir] = useState({ x: 1, y: 0 });
  const [nextDir, setNextDir] = useState({ x: 1, y: 0 });
  const [gameState, setGameState] = useState<'idle' | 'playing' | 'over'>('idle');
  const [score, setScore] = useState(0);
  const [highScore, setHighScore] = useState(() =>
    parseInt(localStorage.getItem('snake_hs') || '0')
  );
  const speedRef = useRef(INITIAL_SPEED);
  const gameLoopRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);

  const placeFood = useCallback((snakeBody: typeof snake) => {
    let pos: { x: number; y: number };
    do {
      pos = { x: Math.floor(Math.random() * GRID_W), y: Math.floor(Math.random() * GRID_H) };
    } while (snakeBody.some((s) => s.x === pos.x && s.y === pos.y));
    return pos;
  }, []);

  const startGame = () => {
    const startSnake = [{ x: 12, y: 10 }];
    setSnake(startSnake);
    setFood(placeFood(startSnake));
    setDir({ x: 1, y: 0 });
    setNextDir({ x: 1, y: 0 });
    setScore(0);
    speedRef.current = INITIAL_SPEED;
    setGameState('playing');
  };

  useEffect(() => {
    if (gameState !== 'playing') return;

    gameLoopRef.current = setInterval(() => {
      setDir((currentDir) => {
        setSnake((prev) => {
          const newSnake = [...prev];
          const head = { ...newSnake[0] };
          head.x += nextDir.x;
          head.y += nextDir.y;

          if (
            head.x < 0 ||
            head.x >= GRID_W ||
            head.y < 0 ||
            head.y >= GRID_H ||
            newSnake.some((s) => s.x === head.x && s.y === head.y)
          ) {
            setGameState('over');
            return prev;
          }

          newSnake.unshift(head);

          let ate = false;
          setFood((currentFood) => {
            if (head.x === currentFood.x && head.y === currentFood.y) {
              ate = true;
              setScore((s) => {
                const newScore = s + 10;
                if (newScore > highScore) {
                  setHighScore(newScore);
                  localStorage.setItem('snake_hs', String(newScore));
                }
                return newScore;
              });
              speedRef.current = Math.max(60, INITIAL_SPEED - Math.floor(newSnake.length / 5) * 8);
              return placeFood(newSnake);
            }
            return currentFood;
          });

          if (!ate) newSnake.pop();
          return newSnake;
        });
        return nextDir;
      });
    }, speedRef.current);

    return () => clearInterval(gameLoopRef.current);
  }, [gameState, nextDir, highScore, placeFood]);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (gameState !== 'playing') return;
      switch (e.key) {
        case 'ArrowUp':
          if (dir.y === 0) setNextDir({ x: 0, y: -1 });
          break;
        case 'ArrowDown':
          if (dir.y === 0) setNextDir({ x: 0, y: 1 });
          break;
        case 'ArrowLeft':
          if (dir.x === 0) setNextDir({ x: -1, y: 0 });
          break;
        case 'ArrowRight':
          if (dir.x === 0) setNextDir({ x: 1, y: 0 });
          break;
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [gameState, dir]);

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 items-center justify-center p-4">
      <div className="flex items-center justify-between w-full max-w-[400px] mb-2">
        <div className="text-xs text-blue-300/50">
          Score: <span className="text-blue-200">{score}</span>
        </div>
        <div className="flex items-center gap-1 text-xs text-blue-300/30">
          <Trophy size={12} /> {highScore}
        </div>
      </div>

      <div
        className="relative bg-[#0a1420] rounded-xl border border-blue-500/15 p-2"
        style={{ width: GRID_W * 16, height: GRID_H * 16 }}
      >
        {gameState === 'idle' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#0a1420]/90 z-10 rounded-xl">
            <div className="text-3xl mb-2">🐍</div>
            <h2 className="text-lg text-blue-200 mb-1">Snake</h2>
            <p className="text-xs text-blue-300/40 mb-4">Use arrow keys to move</p>
            <button
              onClick={startGame}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-500/20 hover:bg-blue-500/30 text-blue-200 text-sm transition-colors"
            >
              <Play size={16} /> Start
            </button>
          </div>
        )}
        {gameState === 'over' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#0a1420]/90 z-10 rounded-xl">
            <h2 className="text-lg text-red-400 mb-1">Game Over</h2>
            <p className="text-sm text-blue-200 mb-1">Score: {score}</p>
            {score >= highScore && score > 0 && (
              <p className="text-xs text-yellow-400 mb-3">New High Score!</p>
            )}
            <button
              onClick={startGame}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-500/20 hover:bg-blue-500/30 text-blue-200 text-sm transition-colors"
            >
              <RotateCcw size={16} /> Retry
            </button>
          </div>
        )}
        {/* Grid */}
        {Array.from({ length: GRID_H }).map((_, y) =>
          Array.from({ length: GRID_W }).map((_, x) => {
            const isSnake = snake.some((s, i) => s.x === x && s.y === y);
            const isHead = snake[0]?.x === x && snake[0]?.y === y;
            const isFood = food.x === x && food.y === y;
            return (
              <div
                key={`${x}-${y}`}
                className="absolute"
                style={{
                  left: x * 16 + 8,
                  top: y * 16 + 8,
                  width: 14,
                  height: 14,
                  borderRadius: isFood ? '50%' : isHead ? '4px' : '2px',
                  background: isFood
                    ? '#ef4444'
                    : isHead
                      ? '#60a5fa'
                      : isSnake
                        ? '#3b82f6'
                        : 'transparent',
                  boxShadow: isHead
                    ? '0 0 8px rgba(96,165,250,0.4)'
                    : isFood
                      ? '0 0 6px rgba(239,68,68,0.4)'
                      : 'none',
                }}
              />
            );
          })
        )}
      </div>

      {/* Mobile Controls */}
      <div className="mt-3 grid grid-cols-3 gap-1 w-28">
        <div />
        <button
          onClick={() => gameState === 'playing' && dir.y === 0 && setNextDir({ x: 0, y: -1 })}
          className="h-8 rounded bg-blue-500/10 text-blue-300 hover:bg-blue-500/20 text-xs"
        >
          ▲
        </button>
        <div />
        <button
          onClick={() => gameState === 'playing' && dir.x === 0 && setNextDir({ x: -1, y: 0 })}
          className="h-8 rounded bg-blue-500/10 text-blue-300 hover:bg-blue-500/20 text-xs"
        >
          ◀
        </button>
        <button
          onClick={() => gameState === 'playing' && dir.y === 0 && setNextDir({ x: 0, y: 1 })}
          className="h-8 rounded bg-blue-500/10 text-blue-300 hover:bg-blue-500/20 text-xs"
        >
          ▼
        </button>
        <button
          onClick={() => gameState === 'playing' && dir.x === 0 && setNextDir({ x: 1, y: 0 })}
          className="h-8 rounded bg-blue-500/10 text-blue-300 hover:bg-blue-500/20 text-xs"
        >
          ▶
        </button>
      </div>
    </div>
  );
}
