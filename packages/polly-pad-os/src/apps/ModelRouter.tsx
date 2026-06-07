import React, { useState, useEffect } from 'react';
import { Cpu, TrendingUp, Zap, Globe, DollarSign, Activity } from 'lucide-react';

const MODELS = [
  {
    id: 'claude-sonnet',
    name: 'Claude 3.5 Sonnet',
    provider: 'Anthropic',
    status: 'active',
    latency: 420,
    throughput: 45,
    costPer1k: 0.003,
    tokensIn: 892000,
    tokensOut: 156000,
    accuracy: 94,
  },
  {
    id: 'gpt-4o',
    name: 'GPT-4o',
    provider: 'OpenAI',
    status: 'active',
    latency: 380,
    throughput: 52,
    costPer1k: 0.005,
    tokensIn: 1234000,
    tokensOut: 234000,
    accuracy: 93,
  },
  {
    id: 'claude-haiku',
    name: 'Claude 3.5 Haiku',
    provider: 'Anthropic',
    status: 'active',
    latency: 120,
    throughput: 120,
    costPer1k: 0.00025,
    tokensIn: 2345000,
    tokensOut: 456000,
    accuracy: 87,
  },
  {
    id: 'gpt-4o-mini',
    name: 'GPT-4o Mini',
    provider: 'OpenAI',
    status: 'active',
    latency: 95,
    throughput: 145,
    costPer1k: 0.00015,
    tokensIn: 3456000,
    tokensOut: 678000,
    accuracy: 84,
  },
  {
    id: 'llama-3',
    name: 'Llama 3.1 70B',
    provider: 'Meta',
    status: 'standby',
    latency: 890,
    throughput: 18,
    costPer1k: 0.0009,
    tokensIn: 0,
    tokensOut: 0,
    accuracy: 89,
  },
  {
    id: 'codestral',
    name: 'Codestral',
    provider: 'Mistral',
    status: 'active',
    latency: 560,
    throughput: 32,
    costPer1k: 0.001,
    tokensIn: 456000,
    tokensOut: 89000,
    accuracy: 91,
  },
];

export default function ModelRouter() {
  const [models, setModels] = useState(MODELS);
  const [totalCost, setTotalCost] = useState(12.45);
  const [totalTokens, setTotalTokens] = useState(8934000);
  const [routingMode, setRoutingMode] = useState<'auto' | 'manual' | 'cost-optimal' | 'quality'>(
    'auto'
  );

  useEffect(() => {
    const interval = setInterval(() => {
      setModels((prev) =>
        prev.map((m) => ({
          ...m,
          latency: Math.max(50, m.latency + Math.floor((Math.random() - 0.5) * 20)),
          tokensIn:
            m.status === 'active' ? m.tokensIn + Math.floor(Math.random() * 500) : m.tokensIn,
          tokensOut:
            m.status === 'active' ? m.tokensOut + Math.floor(Math.random() * 200) : m.tokensOut,
        }))
      );
      setTotalTokens(models.reduce((s, m) => s + m.tokensIn + m.tokensOut, 0));
      setTotalCost(parseFloat((totalCost + Math.random() * 0.01).toFixed(3)));
    }, 3000);
    return () => clearInterval(interval);
  }, [models, totalCost]);

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-blue-500/10 bg-[#111d2e]">
        <div className="flex items-center gap-2">
          <Cpu size={18} className="text-blue-400" />
          <h2 className="text-sm font-semibold text-blue-200">Model Router</h2>
        </div>
        <div className="flex gap-2">
          {(['auto', 'cost-optimal', 'quality', 'manual'] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setRoutingMode(mode)}
              className={`px-2.5 py-1 rounded-lg text-[10px] transition-colors ${routingMode === mode ? 'bg-blue-500/20 text-blue-200' : 'text-blue-300/30 hover:text-blue-200/60'}`}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>

      {/* Cost Dashboard */}
      <div className="grid grid-cols-3 gap-3 p-4">
        <div className="bg-[#162032] rounded-xl p-3 border border-blue-500/10">
          <div className="flex items-center gap-2 mb-1">
            <DollarSign size={14} className="text-green-400" />
            <span className="text-[10px] text-blue-300/30">Session Cost</span>
          </div>
          <div className="text-xl text-blue-200 font-light">${totalCost.toFixed(2)}</div>
        </div>
        <div className="bg-[#162032] rounded-xl p-3 border border-blue-500/10">
          <div className="flex items-center gap-2 mb-1">
            <Activity size={14} className="text-blue-400" />
            <span className="text-[10px] text-blue-300/30">Total Tokens</span>
          </div>
          <div className="text-xl text-blue-200 font-light">
            {(totalTokens / 1000000).toFixed(2)}M
          </div>
        </div>
        <div className="bg-[#162032] rounded-xl p-3 border border-blue-500/10">
          <div className="flex items-center gap-2 mb-1">
            <Globe size={14} className="text-purple-400" />
            <span className="text-[10px] text-blue-300/30">Active Models</span>
          </div>
          <div className="text-xl text-blue-200 font-light">
            {models.filter((m) => m.status === 'active').length}/{models.length}
          </div>
        </div>
      </div>

      {/* Model Table */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        <div className="text-[10px] uppercase tracking-wider text-blue-400/30 mb-2">
          Model Endpoints
        </div>
        <div className="space-y-2">
          {models.map((m) => (
            <div key={m.id} className="bg-[#162032] rounded-xl p-3 border border-blue-500/10">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div
                    className={`w-2 h-2 rounded-full ${m.status === 'active' ? 'bg-green-400' : 'bg-yellow-400'}`}
                  />
                  <span className="text-xs text-blue-200 font-medium">{m.name}</span>
                  <span className="text-[10px] text-blue-300/20">{m.provider}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-[10px] text-blue-300/30">${m.costPer1k}/1K</span>
                  <div className="flex items-center gap-1">
                    <Zap
                      size={10}
                      className={
                        m.latency < 300
                          ? 'text-green-400'
                          : m.latency < 600
                            ? 'text-yellow-400'
                            : 'text-red-400'
                      }
                    />
                    <span className="text-[10px] text-blue-300/40">{m.latency}ms</span>
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-4 gap-2 text-[10px]">
                <div className="bg-[#0d1926] rounded p-1.5 text-center">
                  <div className="text-blue-300/20 mb-0.5">Accuracy</div>
                  <div className="text-blue-200">{m.accuracy}%</div>
                </div>
                <div className="bg-[#0d1926] rounded p-1.5 text-center">
                  <div className="text-blue-300/20 mb-0.5">Throughput</div>
                  <div className="text-blue-200">{m.throughput}/s</div>
                </div>
                <div className="bg-[#0d1926] rounded p-1.5 text-center">
                  <div className="text-blue-300/20 mb-0.5">In</div>
                  <div className="text-blue-200">{(m.tokensIn / 1000).toFixed(0)}k</div>
                </div>
                <div className="bg-[#0d1926] rounded p-1.5 text-center">
                  <div className="text-blue-300/20 mb-0.5">Out</div>
                  <div className="text-blue-200">{(m.tokensOut / 1000).toFixed(0)}k</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
