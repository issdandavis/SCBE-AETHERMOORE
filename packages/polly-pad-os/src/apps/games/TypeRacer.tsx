import React, { useState, useEffect, useRef } from 'react';
import { Play, RotateCcw, Trophy } from 'lucide-react';

const SENTENCES = [
  'The quick brown fox jumps over the lazy dog',
  'Programming is the art of telling another human what one wants the computer to do',
  'The only way to do great work is to love what you do',
  'Simplicity is the ultimate sophistication',
  'Code is like humor when you have to explain it it is bad',
  'Knowledge is power and enthusiasm pulls the switch',
  'The best way to predict the future is to create it',
];

export default function TypeRacer() {
  const [sentence, setSentence] = useState('');
  const [input, setInput] = useState('');
  const [gameState, setGameState] = useState<'idle' | 'playing' | 'done'>('idle');
  const [wpm, setWpm] = useState(0);
  const [accuracy, setAccuracy] = useState(0);
  const [highScore, setHighScore] = useState(() =>
    parseInt(localStorage.getItem('typeracer_hs') || '0')
  );
  const startTime = useRef(0);

  const start = () => {
    setSentence(SENTENCES[Math.floor(Math.random() * SENTENCES.length)]);
    setInput('');
    setGameState('playing');
    startTime.current = Date.now();
  };

  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (gameState !== 'playing') return;
    const val = e.target.value;
    setInput(val);
    if (val === sentence) {
      const time = (Date.now() - startTime.current) / 60000;
      const words = sentence.split(' ').length;
      const calcWpm = Math.round(words / time);
      setWpm(calcWpm);
      let correct = 0;
      for (let i = 0; i < val.length; i++) if (val[i] === sentence[i]) correct++;
      setAccuracy(Math.round((correct / sentence.length) * 100));
      setGameState('done');
      if (calcWpm > highScore) {
        setHighScore(calcWpm);
        localStorage.setItem('typeracer_hs', String(calcWpm));
      }
    }
  };

  const getCharClass = (idx: number) => {
    if (idx >= input.length) return 'text-blue-200/30';
    return input[idx] === sentence[idx] ? 'text-green-400' : 'text-red-400';
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 items-center justify-center p-4">
      <div className="flex items-center gap-2 mb-4">
        <h2 className="text-lg text-blue-200 font-semibold">Type Racer</h2>
        <span className="text-xs text-blue-300/30 flex items-center gap-1">
          <Trophy size={12} /> {highScore} WPM
        </span>
      </div>

      {gameState === 'idle' && (
        <button
          onClick={start}
          className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-blue-500/20 hover:bg-blue-500/30 text-blue-200 text-sm transition-colors"
        >
          <Play size={16} /> Start
        </button>
      )}

      {gameState !== 'idle' && (
        <>
          <div className="text-lg font-mono mb-4 leading-relaxed max-w-[500px] text-center">
            {sentence.split('').map((c, i) => (
              <span key={i} className={getCharClass(i)}>
                {c}
              </span>
            ))}
          </div>
          <input
            value={input}
            onChange={handleInput}
            className="w-full max-w-[500px] bg-[#162032] border border-blue-500/15 rounded-xl px-4 py-2 text-sm font-mono outline-none focus:border-blue-500/30"
            autoFocus
            disabled={gameState === 'done'}
          />
        </>
      )}

      {gameState === 'done' && (
        <div className="mt-4 text-center">
          <div className="text-2xl text-blue-200 mb-1">{wpm} WPM</div>
          <div className="text-sm text-blue-300/50 mb-3">{accuracy}% accuracy</div>
          <button
            onClick={start}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-500/20 hover:bg-blue-500/30 text-blue-200 text-sm transition-colors"
          >
            <RotateCcw size={14} /> Retry
          </button>
        </div>
      )}
    </div>
  );
}
