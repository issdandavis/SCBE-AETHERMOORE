import React, { useState, useCallback, useEffect } from 'react';
import { Key, Copy, Check, RefreshCw, Shield, ShieldAlert, ShieldCheck } from 'lucide-react';

interface PasswordOptions {
  length: number;
  uppercase: boolean;
  lowercase: boolean;
  numbers: boolean;
  symbols: boolean;
  excludeSimilar: boolean;
}

function generatePassword(options: PasswordOptions): string {
  const chars = {
    uppercase: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
    lowercase: 'abcdefghijklmnopqrstuvwxyz',
    numbers: '0123456789',
    symbols: '!@#$%^&*()_+-=[]{}|;:,.<>?',
  };
  let pool = '';
  if (options.uppercase) pool += chars.uppercase;
  if (options.lowercase) pool += chars.lowercase;
  if (options.numbers) pool += chars.numbers;
  if (options.symbols) pool += chars.symbols;
  if (options.excludeSimilar) pool = pool.replace(/[0Oo1lI]/g, '');
  if (!pool) pool = chars.lowercase + chars.numbers;

  const array = new Uint32Array(options.length);
  crypto.getRandomValues(array);
  return Array.from(array, (x) => pool[x % pool.length]).join('');
}

function calcStrength(password: string): { score: number; label: string; color: string } {
  let score = 0;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (password.length >= 16) score++;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[^a-zA-Z0-9]/.test(password)) score++;

  const labels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong', 'Very Strong'];
  const colors = [
    'text-red-500',
    'text-red-400',
    'text-yellow-400',
    'text-blue-400',
    'text-green-400',
    'text-green-300',
  ];
  const idx = Math.min(Math.floor(score / 1.2), 5);
  return { score: idx, label: labels[idx], color: colors[idx] };
}

export default function PasswordGen() {
  const [options, setOptions] = useState<PasswordOptions>({
    length: 16,
    uppercase: true,
    lowercase: true,
    numbers: true,
    symbols: true,
    excludeSimilar: false,
  });
  const [password, setPassword] = useState('');
  const [history, setHistory] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem('linuxos_password_history');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    localStorage.setItem('linuxos_password_history', JSON.stringify(history));
  }, [history]);

  const generate = useCallback(() => {
    const pwd = generatePassword(options);
    setPassword(pwd);
    setHistory((prev) => [pwd, ...prev].slice(0, 20));
  }, [options]);

  useEffect(() => {
    generate();
  }, [generate]);

  const strength = calcStrength(password);
  const strengthIcons = [ShieldAlert, ShieldAlert, Shield, ShieldCheck, ShieldCheck, ShieldCheck];
  const StrengthIcon = strengthIcons[strength.score];

  const copy = () => {
    navigator.clipboard.writeText(password);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 p-4">
      <div className="flex items-center gap-2 mb-4">
        <Key size={18} className="text-blue-400" />
        <h2 className="text-lg text-blue-200 font-semibold">Password Generator</h2>
      </div>

      <div className="bg-[#162032] rounded-xl p-4 border border-blue-500/10 mb-4">
        <div className="flex items-center gap-3 mb-3">
          <div className="flex-1 text-lg font-mono text-blue-100 break-all leading-relaxed">
            {password}
          </div>
          <button
            onClick={copy}
            className="p-2 rounded-lg hover:bg-blue-500/20 text-blue-300/40 hover:text-blue-300 transition-colors flex-shrink-0"
          >
            {copied ? <Check size={16} className="text-green-400" /> : <Copy size={16} />}
          </button>
          <button
            onClick={generate}
            className="p-2 rounded-lg hover:bg-blue-500/20 text-blue-300/40 hover:text-blue-300 transition-colors flex-shrink-0"
          >
            <RefreshCw size={16} />
          </button>
        </div>
        <div className="flex items-center gap-2">
          <StrengthIcon size={14} className={strength.color} />
          <div className="flex-1 h-1.5 bg-blue-500/10 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-300 ${strength.color.replace('text-', 'bg-')}`}
              style={{ width: `${((strength.score + 1) / 6) * 100}%` }}
            />
          </div>
          <span className={`text-[10px] ${strength.color}`}>{strength.label}</span>
        </div>
      </div>

      <div className="space-y-3 mb-4">
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-blue-300/50">Length</span>
            <span className="text-xs text-blue-200 font-mono">{options.length}</span>
          </div>
          <input
            type="range"
            min={4}
            max={64}
            value={options.length}
            onChange={(e) => setOptions({ ...options, length: Number(e.target.value) })}
            className="w-full accent-blue-500"
          />
          <div className="flex justify-between text-[9px] text-blue-400/20 mt-0.5">
            <span>4</span>
            <span>16</span>
            <span>32</span>
            <span>64</span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2">
          {[
            { key: 'uppercase', label: 'Uppercase (A-Z)' },
            { key: 'lowercase', label: 'Lowercase (a-z)' },
            { key: 'numbers', label: 'Numbers (0-9)' },
            { key: 'symbols', label: 'Symbols (!@#$)' },
          ].map(({ key, label }) => (
            <label
              key={key}
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[#162032] border border-blue-500/5 cursor-pointer hover:border-blue-500/15 transition-colors"
            >
              <input
                type="checkbox"
                checked={options[key as keyof PasswordOptions] as boolean}
                onChange={(e) => setOptions({ ...options, [key]: e.target.checked })}
                className="accent-blue-500"
              />
              <span className="text-xs text-blue-200/60">{label}</span>
            </label>
          ))}
        </div>

        <label className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[#162032] border border-blue-500/5 cursor-pointer hover:border-blue-500/15 transition-colors">
          <input
            type="checkbox"
            checked={options.excludeSimilar}
            onChange={(e) => setOptions({ ...options, excludeSimilar: e.target.checked })}
            className="accent-blue-500"
          />
          <span className="text-xs text-blue-200/60">Exclude similar (0, O, 1, l, I)</span>
        </label>
      </div>

      {history.length > 1 && (
        <div className="flex-1 overflow-hidden">
          <div className="text-[10px] uppercase tracking-wider text-blue-400/30 mb-1">History</div>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {history.slice(1, 11).map((h, i) => (
              <button
                key={i}
                onClick={() => setPassword(h)}
                className="w-full text-left px-2 py-1 rounded bg-[#162032] text-[10px] text-blue-200/40 hover:text-blue-200/70 font-mono transition-colors truncate"
              >
                {h}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
