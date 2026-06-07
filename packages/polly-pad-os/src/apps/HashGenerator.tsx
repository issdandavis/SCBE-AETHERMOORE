import React, { useState, useCallback, useEffect } from 'react';
import { Hash, Copy, Check, FileText, RefreshCw } from 'lucide-react';

type HashAlgo = 'SHA-1' | 'SHA-256' | 'SHA-384' | 'SHA-512' | 'MD5';

// MD5 implementation since Web Crypto doesn't support it
function md5(message: string): string {
  const hexChars = '0123456789abcdef';
  const S = [
    7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22, 5, 9, 14, 20, 5, 9, 14, 20, 5, 9,
    14, 20, 5, 9, 14, 20, 4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23, 6, 10, 15, 21,
    6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21,
  ];
  const K = new Uint32Array(64);
  for (let i = 0; i < 64; i++) K[i] = Math.floor(Math.abs(Math.sin(i + 1)) * 4294967296);

  let a0 = 0x67452301,
    b0 = 0xefcdab89,
    c0 = 0x98badcfe,
    d0 = 0x10325476;
  const msg = new TextEncoder().encode(message);
  const bitLen = msg.length * 8;
  const paddedLen = Math.ceil((msg.length + 9) / 64) * 64;
  const padded = new Uint8Array(paddedLen);
  padded.set(msg);
  padded[msg.length] = 0x80;
  const view = new DataView(padded.buffer);
  view.setUint32(paddedLen - 4, bitLen, true);

  for (let i = 0; i < paddedLen; i += 64) {
    const w = new Uint32Array(16);
    for (let j = 0; j < 16; j++) w[j] = view.getUint32(i + j * 4, true);
    let [a, b, c, d] = [a0, b0, c0, d0];
    for (let j = 0; j < 64; j++) {
      let f, g;
      if (j < 16) {
        f = (b & c) | (~b & d);
        g = j;
      } else if (j < 32) {
        f = (d & b) | (~d & c);
        g = (5 * j + 1) % 16;
      } else if (j < 48) {
        f = b ^ c ^ d;
        g = (3 * j + 5) % 16;
      } else {
        f = c ^ (b | ~d);
        g = (7 * j) % 16;
      }
      const temp = d;
      d = c;
      c = b;
      b = b + leftRotate(a + f + K[j] + w[g], S[j]);
      a = temp;
    }
    a0 += a;
    b0 += b;
    c0 += c;
    d0 += d;
  }

  function leftRotate(x: number, c: number) {
    return (x << c) | (x >>> (32 - c));
  }

  const result = new Uint32Array([a0, b0, c0, d0]);
  let hex = '';
  for (const v of result) {
    for (let i = 0; i < 4; i++) {
      const byte = (v >>> (i * 8)) & 0xff;
      hex += hexChars[(byte >>> 4) & 0xf] + hexChars[byte & 0xf];
    }
  }
  return hex;
}

export default function HashGenerator() {
  const [input, setInput] = useState('');
  const [hashes, setHashes] = useState<Record<HashAlgo, string>>({
    'SHA-1': '',
    'SHA-256': '',
    'SHA-384': '',
    'SHA-512': '',
    MD5: '',
  });
  const [copied, setCopied] = useState<string | null>(null);
  const [fileName, setFileName] = useState('');

  const computeHashes = useCallback(async (text: string) => {
    if (!text) {
      setHashes({ 'SHA-1': '', 'SHA-256': '', 'SHA-384': '', 'SHA-512': '', MD5: '' });
      return;
    }
    const encoder = new TextEncoder();
    const data = encoder.encode(text);

    const results: Partial<Record<HashAlgo, string>> = {};

    // MD5
    results['MD5'] = md5(text);

    // Web Crypto algorithms
    const algos: ('SHA-1' | 'SHA-256' | 'SHA-384' | 'SHA-512')[] = [
      'SHA-1',
      'SHA-256',
      'SHA-384',
      'SHA-512',
    ];
    for (const algo of algos) {
      try {
        const hashBuffer = await crypto.subtle.digest(algo, data);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        results[algo] = hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
      } catch {
        results[algo] = 'Error';
      }
    }
    setHashes(results as Record<HashAlgo, string>);
  }, []);

  useEffect(() => {
    computeHashes(input);
  }, [input, computeHashes]);

  const copy = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopied(label);
    setTimeout(() => setCopied(null), 1500);
  };

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (ev) => {
      setInput(ev.target?.result as string);
    };
    reader.readAsText(file);
  };

  const clear = () => {
    setInput('');
    setFileName('');
  };

  const algoColors: Record<HashAlgo, string> = {
    MD5: 'text-yellow-300/70',
    'SHA-1': 'text-orange-300/70',
    'SHA-256': 'text-green-300/70',
    'SHA-384': 'text-blue-300/70',
    'SHA-512': 'text-purple-300/70',
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 p-4 overflow-hidden">
      <div className="flex items-center gap-2 mb-3">
        <Hash size={18} className="text-blue-400" />
        <h2 className="text-lg text-blue-200 font-semibold">Hash Generator</h2>
      </div>

      <div className="flex gap-2 mb-3">
        <label className="px-3 py-1.5 rounded-lg bg-blue-500/15 text-blue-300 text-xs hover:bg-blue-500/25 transition-colors cursor-pointer flex items-center gap-1.5">
          <FileText size={12} /> File
          <input type="file" onChange={handleFile} className="hidden" />
        </label>
        {fileName && <span className="text-[10px] text-blue-300/30 self-center">{fileName}</span>}
        <div className="flex-1" />
        <button
          onClick={clear}
          className="px-3 py-1.5 rounded-lg bg-red-500/10 text-red-300 text-xs hover:bg-red-500/20 transition-colors flex items-center gap-1.5"
        >
          <RefreshCw size={12} /> Clear
        </button>
      </div>

      <textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Enter text to hash..."
        className="h-24 bg-[#162032] border border-blue-500/15 rounded-xl p-3 text-xs resize-none outline-none focus:border-blue-500/30 mb-3 font-mono"
      />

      <div className="flex-1 overflow-y-auto space-y-2">
        {(Object.entries(hashes) as [HashAlgo, string][])
          .filter(([, v]) => v)
          .map(([algo, hash]) => (
            <div key={algo} className="bg-[#162032] rounded-xl p-3 border border-blue-500/5">
              <div className="flex items-center justify-between mb-1">
                <span className={`text-xs font-semibold ${algoColors[algo]}`}>{algo}</span>
                <button
                  onClick={() => copy(hash, algo)}
                  className="p-1 rounded hover:bg-blue-500/20 text-blue-300/30 hover:text-blue-300 transition-colors"
                >
                  {copied === algo ? (
                    <Check size={12} className="text-green-400" />
                  ) : (
                    <Copy size={12} />
                  )}
                </button>
              </div>
              <div className="text-[10px] text-blue-200/50 font-mono break-all leading-relaxed">
                {hash}
              </div>
            </div>
          ))}
        {!input && (
          <div className="text-xs text-blue-400/20 text-center py-4">
            Enter text or select a file to generate hashes
          </div>
        )}
      </div>
    </div>
  );
}
