import React, { useState } from 'react';
import { RotateCcw } from 'lucide-react';

const SUITS = ['♠', '♥', '♦', '♣'];
const RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'];
const SUIT_COLORS: Record<string, string> = {
  '♠': 'text-blue-300',
  '♣': 'text-blue-300',
  '♥': 'text-red-400',
  '♦': 'text-red-400',
};

function createDeck() {
  const deck = SUITS.flatMap((s) =>
    RANKS.map((r) => ({ suit: s, rank: r, color: SUIT_COLORS[s] }))
  );
  for (let i = deck.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [deck[i], deck[j]] = [deck[j], deck[i]];
  }
  return deck;
}

export default function Solitaire() {
  const [tableau, setTableau] = useState(() => {
    const deck = createDeck();
    const tab: (typeof deck)[] = [];
    let idx = 0;
    for (let i = 0; i < 7; i++) {
      tab.push(deck.slice(idx, idx + i + 1));
      idx += i + 1;
    }
    return tab;
  });
  const [stock, setStock] = useState(() => {
    const deck = createDeck();
    let idx = 0;
    for (let i = 0; i < 7; i++) idx += i + 1;
    return deck.slice(idx);
  });
  const [waste, setWaste] = useState<typeof stock>([]);
  const [foundations, setFoundations] = useState<(typeof stock)[]>([[], [], [], []]);
  const [selected, setSelected] = useState<{ pile: number; cardIdx: number } | null>(null);

  const drawCard = () => {
    if (stock.length === 0) {
      setStock([...waste].reverse());
      setWaste([]);
      return;
    }
    setWaste((prev) => [...prev, stock[stock.length - 1]]);
    setStock((prev) => prev.slice(0, -1));
  };

  const handleTableauClick = (pileIdx: number, cardIdx: number) => {
    const pile = tableau[pileIdx];
    if (cardIdx < pile.length - 1) return;
    if (!selected) {
      if (pile.length > 0) setSelected({ pile: pileIdx, cardIdx });
    } else {
      if (selected.pile === pileIdx) {
        setSelected(null);
        return;
      }
      // Move from waste to tableau
      if (selected.pile === -1 && waste.length > 0) {
        const card = waste[waste.length - 1];
        if (canPlaceOnTableau(card, pile)) {
          setTableau((prev) => prev.map((p, i) => (i === pileIdx ? [...p, card] : p)));
          setWaste((prev) => prev.slice(0, -1));
        }
      } else {
        const fromPile = tableau[selected.pile];
        const cards = fromPile.slice(selected.cardIdx);
        if (canPlaceOnTableau(cards[0], pile)) {
          setTableau((prev) =>
            prev.map((p, i) =>
              i === pileIdx
                ? [...p, ...cards]
                : i === selected.pile
                  ? p.slice(0, selected.cardIdx)
                  : p
            )
          );
        }
      }
      setSelected(null);
    }
  };

  const canPlaceOnTableau = (card: (typeof stock)[0], pile: typeof stock) => {
    if (pile.length === 0) return card.rank === 'K';
    const top = pile[pile.length - 1];
    const rankIdx = RANKS.indexOf(card.rank);
    const topIdx = RANKS.indexOf(top.rank);
    return rankIdx === topIdx - 1 && card.color !== top.color;
  };

  const moveToFoundation = (pileIdx: number) => {
    const pile = tableau[pileIdx];
    if (pile.length === 0) return;
    const card = pile[pile.length - 1];
    const suitIdx = SUITS.indexOf(card.suit);
    const foundation = foundations[suitIdx];
    const rankIdx = RANKS.indexOf(card.rank);
    if (
      (foundation.length === 0 && card.rank === 'A') ||
      (foundation.length > 0 &&
        RANKS.indexOf(foundation[foundation.length - 1].rank) === rankIdx - 1)
    ) {
      setFoundations((prev) => prev.map((f, i) => (i === suitIdx ? [...f, card] : f)));
      setTableau((prev) => prev.map((p, i) => (i === pileIdx ? p.slice(0, -1) : p)));
    }
  };

  const reset = () => {
    const deck = createDeck();
    const tab: (typeof deck)[] = [];
    let idx = 0;
    for (let i = 0; i < 7; i++) {
      tab.push(deck.slice(idx, idx + i + 1));
      idx += i + 1;
    }
    setTableau(tab);
    setStock(deck.slice(idx));
    setWaste([]);
    setFoundations([[], [], [], []]);
    setSelected(null);
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 p-2 overflow-auto">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-sm text-blue-200">Solitaire</h2>
        <button onClick={reset} className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/50">
          <RotateCcw size={14} />
        </button>
      </div>
      {/* Top row */}
      <div className="flex gap-2 mb-3">
        <button
          onClick={drawCard}
          className="w-12 h-16 rounded-lg bg-[#162032] border border-blue-500/15 flex items-center justify-center text-blue-300/40 hover:bg-[#1a2d45] text-xs"
        >
          {stock.length}
        </button>
        <div className="w-12 h-16 rounded-lg bg-[#162032] border border-blue-500/15 flex items-center justify-center">
          {waste.length > 0 && (
            <span className={`text-sm ${waste[waste.length - 1].color}`}>
              {waste[waste.length - 1].rank}
              {waste[waste.length - 1].suit}
            </span>
          )}
        </div>
        <div className="flex-1" />
        {foundations.map((f, i) => (
          <div
            key={i}
            className="w-12 h-16 rounded-lg bg-[#162032] border border-blue-500/15 flex items-center justify-center text-blue-300/20"
          >
            {f.length > 0 ? (
              <span className={`text-sm ${f[f.length - 1].color}`}>
                {f[f.length - 1].rank}
                {f[f.length - 1].suit}
              </span>
            ) : (
              SUITS[i]
            )}
          </div>
        ))}
      </div>
      {/* Tableau */}
      <div className="flex gap-2 flex-1">
        {tableau.map((pile, pi) => (
          <div key={pi} className="flex-1">
            {pile.map((card, ci) => (
              <button
                key={ci}
                onClick={() => handleTableauClick(pi, ci)}
                onDoubleClick={() => moveToFoundation(pi)}
                className={`w-full h-8 rounded border text-xs flex items-center justify-center -mt-6 first:mt-0 transition-all ${
                  ci === pile.length - 1
                    ? `bg-[#162032] border-blue-500/20 ${card.color} hover:bg-[#1a2d45]`
                    : 'bg-[#111d2e] border-blue-500/5 text-blue-300/20'
                } ${selected?.pile === pi && selected?.cardIdx === ci ? 'ring-1 ring-yellow-400/50' : ''}`}
                style={{ zIndex: ci }}
              >
                {ci === pile.length - 1 ? `${card.rank}${card.suit}` : '◆'}
              </button>
            ))}
            {pile.length === 0 && (
              <button
                onClick={() => handleTableauClick(pi, 0)}
                className="w-full h-16 rounded border border-dashed border-blue-500/10 hover:border-blue-500/20 transition-colors"
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
