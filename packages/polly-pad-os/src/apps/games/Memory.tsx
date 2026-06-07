import React, { useState, useEffect } from 'react';
import { RotateCcw, Trophy } from 'lucide-react';

const EMOJIS = [
  '🎮',
  '🎯',
  '🎨',
  '🎭',
  '🎪',
  '🎬',
  '🎸',
  '🎺',
  '🎻',
  '🎹',
  '🎲',
  '🎳',
  '🎰',
  '🎱',
  '🎣',
  '🏆',
];

export default function Memory() {
  const [cards, setCards] = useState<
    { id: number; emoji: string; flipped: boolean; matched: boolean }[]
  >([]);
  const [flipped, setFlipped] = useState<number[]>([]);
  const [moves, setMoves] = useState(0);
  const [gameState, setGameState] = useState<'idle' | 'playing' | 'won'>('idle');
  const [highScore, setHighScore] = useState(() =>
    parseInt(localStorage.getItem('memory_hs') || '0')
  );

  const initGame = () => {
    const selected = EMOJIS.slice(0, 8);
    const deck = [...selected, ...selected].map((emoji, i) => ({
      id: i,
      emoji,
      flipped: false,
      matched: false,
    }));
    for (let i = deck.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [deck[i], deck[j]] = [deck[j], deck[i]];
    }
    setCards(deck);
    setFlipped([]);
    setMoves(0);
    setGameState('playing');
  };

  useEffect(() => {
    if (flipped.length === 2) {
      const [a, b] = flipped;
      if (cards[a].emoji === cards[b].emoji) {
        setCards((prev) => prev.map((c, i) => (i === a || i === b ? { ...c, matched: true } : c)));
        setFlipped([]);
      } else {
        setTimeout(() => {
          setCards((prev) =>
            prev.map((c, i) => (i === a || i === b ? { ...c, flipped: false } : c))
          );
          setFlipped([]);
        }, 800);
      }
    }
  }, [flipped, cards]);

  useEffect(() => {
    if (gameState === 'playing' && cards.length > 0 && cards.every((c) => c.matched)) {
      setGameState('won');
      const score = Math.max(100 - moves, 10);
      if (score > highScore) {
        setHighScore(score);
        localStorage.setItem('memory_hs', String(score));
      }
    }
  }, [cards, gameState, moves, highScore]);

  const handleClick = (i: number) => {
    if (gameState !== 'playing' || cards[i].flipped || cards[i].matched || flipped.length >= 2)
      return;
    setCards((prev) => prev.map((c, idx) => (idx === i ? { ...c, flipped: true } : c)));
    setFlipped((prev) => [...prev, i]);
    if (flipped.length === 1) setMoves((m) => m + 1);
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 items-center justify-center p-4">
      <div className="flex items-center justify-between w-full max-w-[400px] mb-3">
        <div className="text-xs text-blue-300/50">
          Moves: <span className="text-blue-200">{moves}</span>
        </div>
        <div className="flex items-center gap-1 text-xs text-blue-300/30">
          <Trophy size={12} />
          {highScore}
        </div>
        <button onClick={initGame} className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/50">
          <RotateCcw size={14} />
        </button>
      </div>
      {gameState === 'idle' && (
        <div className="flex flex-col items-center">
          <h2 className="text-xl text-blue-200 mb-2">Memory Match</h2>
          <p className="text-xs text-blue-300/40 mb-4">Find all matching pairs</p>
          <button
            onClick={initGame}
            className="px-6 py-2 rounded-lg bg-blue-500/20 hover:bg-blue-500/30 text-blue-200 text-sm transition-colors"
          >
            Start Game
          </button>
        </div>
      )}
      {gameState !== 'idle' && (
        <div className="grid grid-cols-4 gap-2">
          {cards.map((card, i) => (
            <button
              key={card.id}
              onClick={() => handleClick(i)}
              className={`w-20 h-20 rounded-xl flex items-center justify-center text-3xl transition-all duration-300 ${
                card.flipped || card.matched
                  ? 'bg-[#162032] rotate-0'
                  : 'bg-[#1e3350] hover:bg-[#254060]'
              } ${card.matched ? 'ring-2 ring-green-500/30' : ''}`}
            >
              {card.flipped || card.matched ? card.emoji : '?'}
            </button>
          ))}
        </div>
      )}
      {gameState === 'won' && (
        <p className="mt-3 text-green-400 text-sm">Completed in {moves} moves!</p>
      )}
    </div>
  );
}
