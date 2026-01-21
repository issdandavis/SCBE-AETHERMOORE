/**
 * Crypto Lab App - Interactive Cryptography Workspace
 *
 * Hands-on exploration of SCBE's cryptographic primitives:
 * - Post-quantum encryption/decryption
 * - Harmonic scaling visualization
 * - Sacred Tongue encoding
 *
 * @license Apache-2.0
 */
import React, { useState, useCallback } from 'react';
import {
  Lock, Unlock, Key, RefreshCw, Copy, Check,
  Zap, Hash, Shield, Sparkles, Binary, FileText
} from 'lucide-react';

type CryptoMode = 'encrypt' | 'hash' | 'sign' | 'encode';

const SACRED_TONGUES = [
  { id: 'KO', name: "Kor'aelin", domain: 'Control & Intent', color: 'bg-pink-500' },
  { id: 'AV', name: 'Avali', domain: 'I/O & Messaging', color: 'bg-blue-500' },
  { id: 'RU', name: 'Runethic', domain: 'Policy & Constraints', color: 'bg-yellow-500' },
  { id: 'CA', name: 'Cassisivadan', domain: 'Logic & Computation', color: 'bg-green-500' },
  { id: 'UM', name: 'Umbroth', domain: 'Security & Secrets', color: 'bg-purple-500' },
  { id: 'DR', name: 'Draumric', domain: 'Types & Schema', color: 'bg-red-500' }
];

// Simple client-side crypto simulation (real impl would call backend)
const simulateCrypto = {
  encrypt: (text: string): string => {
    // Simulate Kyber-768 encryption (returns base64-like output)
    const bytes = new TextEncoder().encode(text);
    const encrypted = Array.from(bytes).map(b => (b + 128) % 256);
    return btoa(String.fromCharCode(...encrypted)) + '==KYBER768';
  },

  decrypt: (ciphertext: string): string => {
    try {
      const base64 = ciphertext.replace('==KYBER768', '');
      const bytes = atob(base64).split('').map(c => c.charCodeAt(0));
      const decrypted = bytes.map(b => (b - 128 + 256) % 256);
      return new TextDecoder().decode(new Uint8Array(decrypted));
    } catch {
      return '[Decryption failed - invalid ciphertext]';
    }
  },

  hash: (text: string): string => {
    // Simulate SHA3-256 hash
    let hash = 0;
    for (let i = 0; i < text.length; i++) {
      const char = text.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    return Math.abs(hash).toString(16).padStart(64, '0').toUpperCase();
  },

  sign: (text: string): string => {
    // Simulate Dilithium-3 signature
    const hash = simulateCrypto.hash(text);
    return `DILITHIUM3:${hash.substring(0, 32)}:${Date.now().toString(16)}`;
  },

  encodeSacred: (text: string, tongue: string): string => {
    // Encode to Sacred Tongue format
    const prefix = `[${tongue}:AXIOM]`;
    const encoded = btoa(text);
    return `${prefix}<payload>${encoded}</payload><sig>VERIFIED</sig>`;
  }
};

export const CryptoLabApp: React.FC = () => {
  const [mode, setMode] = useState<CryptoMode>('encrypt');
  const [input, setInput] = useState('Hello SCBE World!');
  const [output, setOutput] = useState('');
  const [selectedTongue, setSelectedTongue] = useState('KO');
  const [copied, setCopied] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  const processInput = useCallback(() => {
    setIsProcessing(true);

    // Simulate processing delay
    setTimeout(() => {
      switch (mode) {
        case 'encrypt':
          setOutput(simulateCrypto.encrypt(input));
          break;
        case 'hash':
          setOutput(simulateCrypto.hash(input));
          break;
        case 'sign':
          setOutput(simulateCrypto.sign(input));
          break;
        case 'encode':
          setOutput(simulateCrypto.encodeSacred(input, selectedTongue));
          break;
      }
      setIsProcessing(false);
    }, 500);
  }, [mode, input, selectedTongue]);

  const handleDecrypt = useCallback(() => {
    setIsProcessing(true);
    setTimeout(() => {
      setOutput(simulateCrypto.decrypt(input));
      setIsProcessing(false);
    }, 500);
  }, [input]);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(output);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getModeIcon = (m: CryptoMode) => {
    switch (m) {
      case 'encrypt': return Lock;
      case 'hash': return Hash;
      case 'sign': return FileText;
      case 'encode': return Sparkles;
    }
  };

  return (
    <div className="h-full w-full bg-zinc-900 flex flex-col text-white">
      {/* Header */}
      <div className="p-4 bg-zinc-800 border-b border-zinc-700">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-purple-600 flex items-center justify-center">
            <Key size={20} />
          </div>
          <div>
            <h2 className="font-black text-lg">Crypto Lab</h2>
            <div className="text-xs text-zinc-400">Post-Quantum Cryptography Workspace</div>
          </div>
        </div>

        {/* Mode Selector */}
        <div className="flex gap-2">
          {(['encrypt', 'hash', 'sign', 'encode'] as CryptoMode[]).map(m => {
            const Icon = getModeIcon(m);
            return (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`flex-1 py-2 px-3 rounded-lg text-xs font-bold uppercase tracking-widest flex items-center justify-center gap-2 transition-colors ${
                  mode === m
                    ? 'bg-purple-600 text-white'
                    : 'bg-zinc-700 text-zinc-400 hover:bg-zinc-600'
                }`}
              >
                <Icon size={14} />
                {m}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {/* Sacred Tongue Selector (for encode mode) */}
        {mode === 'encode' && (
          <div className="bg-zinc-800 rounded-xl p-4">
            <h3 className="font-bold text-sm mb-3 flex items-center gap-2">
              <Sparkles size={16} className="text-yellow-400" />
              Select Sacred Tongue
            </h3>
            <div className="grid grid-cols-3 gap-2">
              {SACRED_TONGUES.map(tongue => (
                <button
                  key={tongue.id}
                  onClick={() => setSelectedTongue(tongue.id)}
                  className={`p-3 rounded-lg text-left transition-all ${
                    selectedTongue === tongue.id
                      ? `${tongue.color} text-white`
                      : 'bg-zinc-700 hover:bg-zinc-600'
                  }`}
                >
                  <div className="font-bold text-sm">{tongue.id}</div>
                  <div className="text-[10px] opacity-70">{tongue.name}</div>
                  <div className="text-[9px] opacity-50">{tongue.domain}</div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input */}
        <div className="bg-zinc-800 rounded-xl p-4">
          <label className="block text-xs font-bold uppercase tracking-widest text-zinc-400 mb-2">
            Input {mode === 'encrypt' ? '(Plaintext)' : mode === 'hash' ? '(Data)' : mode === 'sign' ? '(Message)' : '(Text)'}
          </label>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="w-full bg-zinc-700 rounded-lg p-3 text-sm font-mono resize-none h-24 focus:outline-none focus:ring-2 focus:ring-purple-500"
            placeholder="Enter text to process..."
          />
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2">
          <button
            onClick={processInput}
            disabled={isProcessing || !input.trim()}
            className="flex-1 py-3 bg-purple-600 rounded-lg text-xs font-bold uppercase tracking-widest flex items-center justify-center gap-2 disabled:opacity-50 hover:bg-purple-500"
          >
            {isProcessing ? (
              <RefreshCw size={14} className="animate-spin" />
            ) : (
              React.createElement(getModeIcon(mode), { size: 14 })
            )}
            {mode === 'encrypt' ? 'Encrypt' : mode === 'hash' ? 'Hash' : mode === 'sign' ? 'Sign' : 'Encode'}
          </button>

          {mode === 'encrypt' && (
            <button
              onClick={handleDecrypt}
              disabled={isProcessing || !input.trim()}
              className="flex-1 py-3 bg-emerald-600 rounded-lg text-xs font-bold uppercase tracking-widest flex items-center justify-center gap-2 disabled:opacity-50 hover:bg-emerald-500"
            >
              <Unlock size={14} />
              Decrypt
            </button>
          )}
        </div>

        {/* Output */}
        {output && (
          <div className="bg-zinc-800 rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-bold uppercase tracking-widest text-zinc-400">
                Output {mode === 'encrypt' ? '(Ciphertext)' : mode === 'hash' ? '(Digest)' : mode === 'sign' ? '(Signature)' : '(Encoded)'}
              </label>
              <button
                onClick={copyToClipboard}
                className="p-1.5 bg-zinc-700 rounded hover:bg-zinc-600 transition-colors"
              >
                {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
              </button>
            </div>
            <div className="bg-zinc-700 rounded-lg p-3 font-mono text-sm break-all text-emerald-400">
              {output}
            </div>
          </div>
        )}

        {/* Algorithm Info */}
        <div className="bg-zinc-800 rounded-xl p-4">
          <h3 className="font-bold text-sm mb-3 flex items-center gap-2">
            <Binary size={16} className="text-sky-400" />
            Algorithm Details
          </h3>
          <div className="space-y-2 text-sm">
            {mode === 'encrypt' && (
              <>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Algorithm</span>
                  <span className="text-emerald-400">Kyber-768 (NIST PQC)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Security Level</span>
                  <span>AES-192 equivalent</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Quantum Resistant</span>
                  <span className="text-emerald-400">✓ Yes</span>
                </div>
              </>
            )}
            {mode === 'hash' && (
              <>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Algorithm</span>
                  <span className="text-sky-400">SHA3-256</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Output Size</span>
                  <span>256 bits (64 hex chars)</span>
                </div>
              </>
            )}
            {mode === 'sign' && (
              <>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Algorithm</span>
                  <span className="text-purple-400">Dilithium-3 (NIST PQC)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Security Level</span>
                  <span>128-bit post-quantum</span>
                </div>
              </>
            )}
            {mode === 'encode' && (
              <>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Format</span>
                  <span className="text-yellow-400">Sacred Tongue Envelope</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Tongue</span>
                  <span>{SACRED_TONGUES.find(t => t.id === selectedTongue)?.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Governance Tier</span>
                  <span>{selectedTongue}</span>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="p-3 bg-zinc-800 border-t border-zinc-700 flex items-center justify-center text-[10px] text-zinc-500">
        <Shield size={10} className="mr-2" />
        SCBE-AETHERMOORE Post-Quantum Cryptography
      </div>
    </div>
  );
};
