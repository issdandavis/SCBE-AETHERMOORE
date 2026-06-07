import React, { useState } from 'react';

export default function Calculator() {
  const [display, setDisplay] = useState('0');
  const [prev, setPrev] = useState('');
  const [op, setOp] = useState('');
  const [newNum, setNewNum] = useState(true);

  const input = (val: string) => {
    if (newNum) {
      setDisplay(val);
      setNewNum(false);
    } else setDisplay(display === '0' ? val : display + val);
  };

  const operation = (o: string) => {
    setOp(o);
    setPrev(display);
    setNewNum(true);
  };

  const calculate = () => {
    if (!op || !prev) return;
    const a = parseFloat(prev);
    const b = parseFloat(display);
    let r = 0;
    switch (op) {
      case '+':
        r = a + b;
        break;
      case '-':
        r = a - b;
        break;
      case '*':
        r = a * b;
        break;
      case '/':
        r = b === 0 ? NaN : a / b;
        break;
      case '%':
        r = a % b;
        break;
    }
    setDisplay(isNaN(r) ? 'Error' : String(r).slice(0, 12));
    setOp('');
    setPrev('');
    setNewNum(true);
  };

  const clear = () => {
    setDisplay('0');
    setPrev('');
    setOp('');
    setNewNum(true);
  };
  const backspace = () => setDisplay(display.length > 1 ? display.slice(0, -1) : '0');

  const btn = (label: string, onClick: () => void, className = '') => (
    <button
      onClick={onClick}
      className={`h-12 rounded-lg text-sm font-medium transition-all active:scale-95 ${className}`}
    >
      {label}
    </button>
  );

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] p-3">
      <div className="bg-[#111d2e] rounded-xl p-4 mb-3">
        <div className="text-right text-3xl text-blue-100 font-light tracking-wide">{display}</div>
        <div className="text-right text-xs text-blue-400/30 mt-1 h-4">
          {prev} {op}
        </div>
      </div>
      <div className="grid grid-cols-4 gap-2 flex-1">
        {btn('C', clear, 'bg-red-500/20 text-red-400 hover:bg-red-500/30')}
        {btn('←', backspace, 'bg-blue-500/10 text-blue-300 hover:bg-blue-500/20')}
        {btn('%', () => operation('%'), 'bg-blue-500/10 text-blue-300 hover:bg-blue-500/20')}
        {btn('÷', () => operation('/'), 'bg-blue-500/20 text-blue-200 hover:bg-blue-500/30')}
        {btn('7', () => input('7'), 'bg-[#162032] text-blue-200 hover:bg-[#1c2a40]')}
        {btn('8', () => input('8'), 'bg-[#162032] text-blue-200 hover:bg-[#1c2a40]')}
        {btn('9', () => input('9'), 'bg-[#162032] text-blue-200 hover:bg-[#1c2a40]')}
        {btn('×', () => operation('*'), 'bg-blue-500/20 text-blue-200 hover:bg-blue-500/30')}
        {btn('4', () => input('4'), 'bg-[#162032] text-blue-200 hover:bg-[#1c2a40]')}
        {btn('5', () => input('5'), 'bg-[#162032] text-blue-200 hover:bg-[#1c2a40]')}
        {btn('6', () => input('6'), 'bg-[#162032] text-blue-200 hover:bg-[#1c2a40]')}
        {btn('-', () => operation('-'), 'bg-blue-500/20 text-blue-200 hover:bg-blue-500/30')}
        {btn('1', () => input('1'), 'bg-[#162032] text-blue-200 hover:bg-[#1c2a40]')}
        {btn('2', () => input('2'), 'bg-[#162032] text-blue-200 hover:bg-[#1c2a40]')}
        {btn('3', () => input('3'), 'bg-[#162032] text-blue-200 hover:bg-[#1c2a40]')}
        {btn('+', () => operation('+'), 'bg-blue-500/20 text-blue-200 hover:bg-blue-500/30')}
        {btn('0', () => input('0'), 'bg-[#162032] text-blue-200 hover:bg-[#1c2a40] col-span-2')}
        {btn('.', () => input('.'), 'bg-[#162032] text-blue-200 hover:bg-[#1c2a40]')}
        {btn('=', calculate, 'bg-blue-600 text-white hover:bg-blue-500')}
      </div>
    </div>
  );
}
