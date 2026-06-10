import React, { useState } from 'react';
import { RotateCcw } from 'lucide-react';

const WORDS = [
  'REACT',
  'LINUX',
  'MOUSE',
  'CLOUD',
  'PIZZA',
  'BEACH',
  'DANCE',
  'MUSIC',
  'FLAME',
  'GHOST',
  'HAPPY',
  'LEMON',
  'NIGHT',
  'OCEAN',
  'PANDA',
  'RIVER',
  'TIGER',
  'WATER',
  'BREAD',
  'CANDY',
  'PIZZA',
  'GRAPE',
  'HOUSE',
  'LIGHT',
  'PLANT',
  'SMILE',
  'STORM',
  'TRAIN',
  'WORLD',
  'YOUTH',
];
const ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');

export default function Hangman() {
  const [word, setWord] = useState(() => WORDS[Math.floor(Math.random() * WORDS.length)]);
  const [guessed, setGuessed] = useState<Set<string>>(new Set());
  const [wrong, setWrong] = useState(0);
  const maxWrong = 6;

  const revealed = word
    .split('')
    .map((c) => (guessed.has(c) ? c : '_'))
    .join(' ');
  const won = !revealed.includes('_');
  const lost = wrong >= maxWrong;

  const guess = (letter: string) => {
    if (guessed.has(letter) || won || lost) return;
    const newGuessed = new Set(guessed);
    newGuessed.add(letter);
    setGuessed(newGuessed);
    if (!word.includes(letter)) setWrong((w) => w + 1);
  };

  const reset = () => {
    setWord(WORDS[Math.floor(Math.random() * WORDS.length)]);
    setGuessed(new Set());
    setWrong(0);
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 items-center justify-center p-4">
      <div className="flex items-center justify-between w-full max-w-[350px] mb-4">
        <h2 className="text-lg text-blue-200">Hangman</h2>
        <button onClick={reset} className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/50">
          <RotateCcw size={14} />
        </button>
      </div>

      {/* Hangman Drawing */}
      <div className="w-32 h-40 relative mb-4">
        <div className="absolute bottom-0 left-4 w-20 h-0.5 bg-blue-400/30" />
        <div className="absolute bottom-0 left-8 w-0.5 h-36 bg-blue-400/30" />
        <div className="absolute top-4 left-8 w-16 h-0.5 bg-blue-400/30" />
        <div className="absolute top-4 left-24 w-0.5 h-6 bg-blue-400/30" />
        {wrong >= 1 && (
          <div className="absolute top-10 left-20 w-8 h-8 rounded-full border-2 border-blue-400/50" />
        )}
        {wrong >= 2 && <div className="absolute top-[58px] left-24 w-0.5 h-14 bg-blue-400/50" />}
        {wrong >= 3 && (
          <div className="absolute top-[66px] left-24 w-8 h-0.5 bg-blue-400/50 origin-left rotate-[30deg]" />
        )}
        {wrong >= 4 && (
          <div className="absolute top-[66px] left-24 w-8 h-0.5 bg-blue-400/50 origin-left rotate-[-30deg]" />
        )}
        {wrong >= 5 && (
          <div className="absolute top-[114px] left-24 w-8 h-0.5 bg-blue-400/50 origin-left rotate-[20deg]" />
        )}
        {wrong >= 6 && (
          <div className="absolute top-[114px] left-24 w-8 h-0.5 bg-blue-400/50 origin-left rotate-[-20deg]" />
        )}
      </div>

      <div className="text-2xl font-mono tracking-widest text-blue-200 mb-4">{revealed}</div>

      {won && <p className="text-green-400 text-sm mb-3">You won!</p>}
      {lost && <p className="text-red-400 text-sm mb-3">The word was: {word}</p>}

      <div className="grid grid-cols-9 gap-1 max-w-[320px]">
        {ALPHABET.map((l) => (
          <button
            key={l}
            onClick={() => guess(l)}
            disabled={guessed.has(l) || won || lost}
            className={`h-8 rounded text-xs font-medium transition-colors ${
              guessed.has(l)
                ? word.includes(l)
                  ? 'bg-green-500/20 text-green-300'
                  : 'bg-red-500/20 text-red-300'
                : 'bg-[#162032] text-blue-200 hover:bg-blue-500/20'
            }`}
          >
            {l}
          </button>
        ))}
      </div>
      <div className="mt-3 text-xs text-blue-300/30">
        Wrong guesses: {wrong}/{maxWrong}
      </div>
    </div>
  );
}
