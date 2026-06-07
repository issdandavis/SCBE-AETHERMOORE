import React, { useState } from 'react';
import { RotateCcw, Trophy } from 'lucide-react';

const QUESTIONS = [
  {
    q: 'What does HTML stand for?',
    options: [
      'Hyper Text Markup Language',
      'High Tech Modern Language',
      'Hyper Transfer Markup Language',
      'Home Tool Markup Language',
    ],
    correct: 0,
  },
  {
    q: 'Which company created React?',
    options: ['Google', 'Microsoft', 'Meta', 'Apple'],
    correct: 2,
  },
  {
    q: 'What is the capital of France?',
    options: ['London', 'Berlin', 'Paris', 'Madrid'],
    correct: 2,
  },
  {
    q: 'What does CPU stand for?',
    options: [
      'Central Process Unit',
      'Central Processing Unit',
      'Computer Personal Unit',
      'Central Processor Unit',
    ],
    correct: 1,
  },
  {
    q: 'Which planet is known as the Red Planet?',
    options: ['Venus', 'Jupiter', 'Mars', 'Saturn'],
    correct: 2,
  },
  { q: 'What is 2^10?', options: ['512', '1024', '2048', '256'], correct: 1 },
  { q: 'What year was Linux created?', options: ['1989', '1991', '1995', '1999'], correct: 1 },
  {
    q: 'Which language runs in a web browser?',
    options: ['Java', 'C', 'Python', 'JavaScript'],
    correct: 3,
  },
];

export default function Quiz() {
  const [current, setCurrent] = useState(0);
  const [score, setScore] = useState(0);
  const [showResult, setShowResult] = useState(false);
  const [selected, setSelected] = useState<number | null>(null);
  const [finished, setFinished] = useState(false);

  const handleAnswer = (idx: number) => {
    if (selected !== null) return;
    setSelected(idx);
    if (idx === QUESTIONS[current].correct) setScore((s) => s + 1);
    setShowResult(true);
  };

  const next = () => {
    if (current + 1 >= QUESTIONS.length) setFinished(true);
    else {
      setCurrent((c) => c + 1);
      setSelected(null);
      setShowResult(false);
    }
  };

  const reset = () => {
    setCurrent(0);
    setScore(0);
    setSelected(null);
    setShowResult(false);
    setFinished(false);
  };

  const q = QUESTIONS[current];

  if (finished) {
    return (
      <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 items-center justify-center p-4">
        <Trophy size={48} className="text-yellow-400 mb-4" />
        <h2 className="text-xl text-blue-200 font-semibold mb-2">Quiz Complete!</h2>
        <p className="text-sm text-blue-300/50 mb-4">
          Score: {score}/{QUESTIONS.length}
        </p>
        <button
          onClick={reset}
          className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-blue-500/20 hover:bg-blue-500/30 text-blue-200 text-sm transition-colors"
        >
          <RotateCcw size={16} /> Restart
        </button>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 p-4">
      <div className="flex items-center justify-between mb-4">
        <span className="text-xs text-blue-300/30">
          Question {current + 1}/{QUESTIONS.length}
        </span>
        <span className="text-xs text-blue-300/30">Score: {score}</span>
      </div>
      <div className="w-full h-1 bg-blue-500/10 rounded-full mb-4">
        <div
          className="h-full bg-blue-500 rounded-full transition-all"
          style={{ width: `${((current + 1) / QUESTIONS.length) * 100}%` }}
        />
      </div>
      <h3 className="text-sm text-blue-200 mb-4">{q.q}</h3>
      <div className="space-y-2 flex-1">
        {q.options.map((opt, i) => (
          <button
            key={i}
            onClick={() => handleAnswer(i)}
            disabled={selected !== null}
            className={`w-full text-left px-4 py-3 rounded-xl text-xs transition-all ${
              selected === null
                ? 'bg-[#162032] text-blue-200/70 hover:bg-blue-500/10 border border-blue-500/5'
                : i === q.correct
                  ? 'bg-green-500/15 text-green-300 border border-green-500/20'
                  : selected === i
                    ? 'bg-red-500/15 text-red-300 border border-red-500/20'
                    : 'bg-[#162032] text-blue-200/30 border border-blue-500/5'
            }`}
          >
            {opt}
          </button>
        ))}
      </div>
      {showResult && (
        <button
          onClick={next}
          className="mt-3 px-4 py-2 rounded-lg bg-blue-500/20 text-blue-200 text-xs hover:bg-blue-500/30 self-end"
        >
          Next
        </button>
      )}
    </div>
  );
}
