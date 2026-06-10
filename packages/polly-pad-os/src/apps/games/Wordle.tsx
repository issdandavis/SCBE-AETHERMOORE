import React, { useState, useEffect } from 'react';
import { RotateCcw, HelpCircle } from 'lucide-react';

const WORDS = [
  'REACT',
  'LINUX',
  'APPLE',
  'MOUSE',
  'CLOUD',
  'ROBOT',
  'PIZZA',
  'BEACH',
  'DANCE',
  'MUSIC',
  'FLAME',
  'GHOST',
  'HAPPY',
  'IMAGE',
  'JUICE',
  'LEMON',
  'NIGHT',
  'OCEAN',
  'PANDA',
  'QUEEN',
  'RIVER',
  'SNAKE',
  'TIGER',
  'UNCLE',
  'VIDEO',
  'WATER',
  'YOUTH',
  'ZEBRA',
  'BREAD',
  'CANDY',
];
const MAX_GUESSES = 6;

export default function Wordle() {
  const [target, setTarget] = useState(() => WORDS[Math.floor(Math.random() * WORDS.length)]);
  const [guesses, setGuesses] = useState<string[]>([]);
  const [current, setCurrent] = useState('');
  const [gameState, setGameState] = useState<'playing' | 'won' | 'lost'>('playing');
  const [shake, setShake] = useState(false);

  useEffect(() => {
    const handle = (e: KeyboardEvent) => {
      if (gameState !== 'playing') return;
      if (e.key === 'Enter' && current.length === 5) submitGuess();
      else if (e.key === 'Backspace') setCurrent((c) => c.slice(0, -1));
      else if (/^[A-Za-z]$/.test(e.key) && current.length < 5)
        setCurrent((c) => c + e.key.toUpperCase());
    };
    window.addEventListener('keydown', handle);
    return () => window.removeEventListener('keydown', handle);
  }, [gameState, current]);

  const submitGuess = () => {
    if (current.length !== 5) return;
    if (
      !WORDS.includes(current) &&
      !['REACT', 'LINUX', 'APPLE', 'MOUSE'].some((w) => w === current)
    ) {
      setShake(true);
      setTimeout(() => setShake(false), 500);
      return;
    }
    const newGuesses = [...guesses, current];
    setGuesses(newGuesses);
    setCurrent('');
    if (current === target) setGameState('won');
    else if (newGuesses.length >= MAX_GUESSES) setGameState('lost');
  };

  const getCellColor = (guess: string, index: number) => {
    const char = guess[index];
    if (target[index] === char) return 'bg-green-500/40 border-green-500/50';
    if (target.includes(char)) return 'bg-yellow-500/40 border-yellow-500/50';
    return 'bg-[#162032] border-blue-500/10';
  };

  const reset = () => {
    setTarget(WORDS[Math.floor(Math.random() * WORDS.length)]);
    setGuesses([]);
    setCurrent('');
    setGameState('playing');
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 items-center justify-center p-4">
      <div className="flex items-center justify-between w-full max-w-[300px] mb-4">
        <h2 className="text-lg text-blue-200 font-semibold">Wordle</h2>
        <button onClick={reset} className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/50">
          <RotateCcw size={14} />
        </button>
      </div>

      <div className={`space-y-1.5 ${shake ? 'animate-pulse' : ''}`}>
        {Array.from({ length: MAX_GUESSES }).map((_, i) => (
          <div key={i} className="flex gap-1.5">
            {Array.from({ length: 5 }).map((_, j) => {
              const char = guesses[i]?.[j] || (i === guesses.length ? current[j] || '' : '');
              return (
                <div
                  key={j}
                  className={`w-12 h-12 rounded-lg border-2 flex items-center justify-center text-lg font-bold transition-all ${
                    guesses[i] ? getCellColor(guesses[i], j) : 'bg-[#162032] border-blue-500/10'
                  }`}
                >
                  {char}
                </div>
              );
            })}
          </div>
        ))}
      </div>

      {gameState === 'won' && <p className="mt-4 text-green-400 text-sm">Congratulations!</p>}
      {gameState === 'lost' && <p className="mt-4 text-red-400 text-sm">The word was: {target}</p>}

      <div className="mt-4 grid grid-cols-10 gap-1 max-w-[380px]">
        {'QWERTYUIOPASDFGHJKLZXCVBNM'.split('').map((letter) => {
          const inTarget = target.includes(letter);
          const guessed = guesses.some((g) => g.includes(letter));
          return (
            <button
              key={letter}
              onClick={() =>
                gameState === 'playing' && current.length < 5 && setCurrent((c) => c + letter)
              }
              className={`h-8 rounded text-xs font-medium transition-colors ${
                guessed && inTarget
                  ? 'bg-yellow-500/30 text-yellow-200'
                  : guessed
                    ? 'bg-[#162032] text-blue-300/30'
                    : 'bg-[#1e3350] text-blue-200 hover:bg-blue-500/20'
              }`}
            >
              {letter}
            </button>
          );
        })}
      </div>
      <div className="flex gap-2 mt-2">
        <button
          onClick={() => setCurrent((c) => c.slice(0, -1))}
          className="px-4 py-1.5 rounded bg-[#1e3350] text-blue-200 text-xs hover:bg-blue-500/20"
        >
          ←
        </button>
        <button
          onClick={submitGuess}
          className="px-4 py-1.5 rounded bg-blue-500/20 text-blue-200 text-xs hover:bg-blue-500/30"
        >
          Enter
        </button>
      </div>
    </div>
  );
}
