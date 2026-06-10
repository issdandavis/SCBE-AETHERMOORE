import React, { useState } from 'react';
import { Play, RotateCcw } from 'lucide-react';

const SUITS = ['♠', '♥', '♦', '♣'];
const RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'];

type Card = { suit: string; rank: string; value: number };

function createDeck(): Card[] {
  const deck: Card[] = [];
  for (const suit of SUITS)
    for (const rank of RANKS) {
      let value = parseInt(rank) || (rank === 'A' ? 11 : 10);
      deck.push({ suit, rank, value });
    }
  for (let i = deck.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [deck[i], deck[j]] = [deck[j], deck[i]];
  }
  return deck;
}

function handValue(hand: Card[]): number {
  let sum = hand.reduce((a, c) => a + c.value, 0);
  let aces = hand.filter((c) => c.rank === 'A').length;
  while (sum > 21 && aces > 0) {
    sum -= 10;
    aces--;
  }
  return sum;
}

export default function Blackjack() {
  const [deck, setDeck] = useState<Card[]>([]);
  const [playerHand, setPlayerHand] = useState<Card[]>([]);
  const [dealerHand, setDealerHand] = useState<Card[]>([]);
  const [gameState, setGameState] = useState<'idle' | 'playing' | 'done'>('idle');
  const [message, setMessage] = useState('');

  const start = () => {
    const d = createDeck();
    const p = [d.pop()!, d.pop()!];
    const h = [d.pop()!, d.pop()!];
    setDeck(d);
    setPlayerHand(p);
    setDealerHand(h);
    setGameState('playing');
    setMessage('');
  };

  const hit = () => {
    const card = deck.pop()!;
    const newHand = [...playerHand, card];
    setPlayerHand(newHand);
    setDeck([...deck]);
    if (handValue(newHand) > 21) {
      setMessage('Bust! Dealer wins.');
      setGameState('done');
    }
  };

  const stand = () => {
    let dHand = [...dealerHand];
    let d = [...deck];
    while (handValue(dHand) < 17) {
      dHand.push(d.pop()!);
    }
    setDealerHand(dHand);
    setDeck(d);
    const pVal = handValue(playerHand);
    const dVal = handValue(dHand);
    if (dVal > 21) setMessage('Dealer busts! You win!');
    else if (pVal > dVal) setMessage('You win!');
    else if (pVal < dVal) setMessage('Dealer wins.');
    else setMessage('Push!');
    setGameState('done');
  };

  const cardColor = (suit: string) =>
    suit === '♥' || suit === '♦' ? 'text-red-400' : 'text-blue-300';

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 items-center justify-center p-4">
      <h2 className="text-lg text-blue-200 font-semibold mb-4">Blackjack</h2>
      {gameState === 'idle' && (
        <button
          onClick={start}
          className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-blue-500/20 hover:bg-blue-500/30 text-blue-200 text-sm transition-colors"
        >
          <Play size={16} /> Deal
        </button>
      )}
      {gameState !== 'idle' && (
        <>
          <div className="mb-4">
            <div className="text-xs text-blue-300/40 mb-1">
              Dealer: {gameState === 'done' ? handValue(dealerHand) : '?'}
            </div>
            <div className="flex gap-2">
              {dealerHand.map((c, i) => (
                <div
                  key={i}
                  className={`w-12 h-16 rounded-lg bg-[#162032] border border-blue-500/15 flex flex-col items-center justify-center text-xs ${gameState === 'playing' && i === 1 ? 'text-blue-300/20' : cardColor(c.suit)}`}
                >
                  {gameState === 'playing' && i === 1 ? (
                    '?'
                  ) : (
                    <>
                      {c.rank}
                      <span className="text-lg">{c.suit}</span>
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>
          <div className="mb-4">
            <div className="text-xs text-blue-300/40 mb-1">You: {handValue(playerHand)}</div>
            <div className="flex gap-2">
              {playerHand.map((c, i) => (
                <div
                  key={i}
                  className={`w-12 h-16 rounded-lg bg-[#162032] border border-blue-500/15 flex flex-col items-center justify-center text-xs ${cardColor(c.suit)}`}
                >
                  {c.rank}
                  <span className="text-lg">{c.suit}</span>
                </div>
              ))}
            </div>
          </div>
          {gameState === 'playing' && (
            <div className="flex gap-2">
              <button
                onClick={hit}
                className="px-4 py-2 rounded-lg bg-blue-500/20 text-blue-200 text-xs hover:bg-blue-500/30"
              >
                Hit
              </button>
              <button
                onClick={stand}
                className="px-4 py-2 rounded-lg bg-green-500/20 text-green-200 text-xs hover:bg-green-500/30"
              >
                Stand
              </button>
            </div>
          )}
          {message && <div className="mt-3 text-sm text-blue-200">{message}</div>}
          {gameState === 'done' && (
            <button
              onClick={start}
              className="mt-3 flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-500/20 text-blue-200 text-xs hover:bg-blue-500/30"
            >
              <RotateCcw size={14} /> New Hand
            </button>
          )}
        </>
      )}
    </div>
  );
}
