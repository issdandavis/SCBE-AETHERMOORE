import React, { useState } from 'react';
import { Activity } from 'lucide-react';

export default function BMI() {
  const [height, setHeight] = useState('');
  const [weight, setWeight] = useState('');
  const [bmi, setBmi] = useState(0);
  const [category, setCategory] = useState('');

  const calculate = () => {
    const h = Number(height) / 100;
    const w = Number(weight);
    if (!h || !w) return;
    const val = w / (h * h);
    setBmi(val);
    if (val < 18.5) setCategory('Underweight');
    else if (val < 25) setCategory('Normal');
    else if (val < 30) setCategory('Overweight');
    else setCategory('Obese');
  };

  const getBarPosition = () => Math.min(100, Math.max(0, ((bmi - 15) / 20) * 100));

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 p-4 items-center justify-center">
      <Activity size={32} className="text-blue-400 mb-4" />
      <h2 className="text-lg text-blue-200 font-semibold mb-4">BMI Calculator</h2>
      <div className="w-full max-w-[260px] space-y-3 mb-4">
        <div>
          <label className="text-xs text-blue-300/40 mb-1 block">Height (cm)</label>
          <input
            type="number"
            value={height}
            onChange={(e) => setHeight(e.target.value)}
            placeholder="175"
            className="w-full bg-[#162032] border border-blue-500/15 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/30"
          />
        </div>
        <div>
          <label className="text-xs text-blue-300/40 mb-1 block">Weight (kg)</label>
          <input
            type="number"
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
            placeholder="70"
            className="w-full bg-[#162032] border border-blue-500/15 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/30"
          />
        </div>
        <button
          onClick={calculate}
          className="w-full py-2 rounded-lg bg-blue-500/20 text-blue-200 text-sm hover:bg-blue-500/30 transition-colors"
        >
          Calculate
        </button>
      </div>
      {bmi > 0 && (
        <div className="w-full max-w-[260px] text-center">
          <div className="text-3xl font-light mb-1">{bmi.toFixed(1)}</div>
          <div
            className={`text-sm mb-3 ${category === 'Normal' ? 'text-green-400' : category === 'Underweight' ? 'text-yellow-400' : 'text-red-400'}`}
          >
            {category}
          </div>
          <div className="w-full h-2 rounded-full bg-gradient-to-r from-blue-500 via-green-500 to-red-500 relative">
            <div
              className="absolute top-0 w-1 h-3 bg-white rounded-full -translate-y-0.5"
              style={{ left: `${getBarPosition()}%` }}
            />
          </div>
          <div className="flex justify-between text-[9px] text-blue-300/20 mt-1">
            <span>15</span>
            <span>18.5</span>
            <span>25</span>
            <span>30</span>
            <span>35</span>
          </div>
        </div>
      )}
    </div>
  );
}
