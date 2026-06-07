import React, { useState, useEffect } from 'react';
import {
  Play,
  Square,
  RotateCcw,
  Plus,
  Trash2,
  Bot,
  User,
  CheckCircle,
  XCircle,
  Clock,
} from 'lucide-react';

interface Agent {
  id: string;
  name: string;
  role: string;
  status: 'idle' | 'running' | 'done' | 'error';
  output: string[];
  model: string;
}

const ROLES = [
  { name: 'Code Explorer', desc: 'Read-only codebase navigation' },
  { name: 'Architect', desc: 'System design & planning' },
  { name: 'Implementer', desc: 'Write code & tests' },
  { name: 'Reviewer', desc: 'Code review & diff analysis' },
  { name: 'Security', desc: 'Vulnerability scanning' },
  { name: 'Debugger', desc: 'Find & fix bugs' },
];

export default function MultiAgentTerminal() {
  const [agents, setAgents] = useState<Agent[]>([
    {
      id: '1',
      name: 'explorer-1',
      role: 'Code Explorer',
      status: 'done',
      output: ['Scanned src/ directory', 'Found 64 components', 'Indexed 12 modules'],
      model: 'claude-sonnet',
    },
    {
      id: '2',
      name: 'architect-1',
      role: 'Architect',
      status: 'running',
      output: [
        'Analyzing system requirements...',
        'Designing module structure...',
        'Creating API contracts...',
      ],
      model: 'gpt-4o',
    },
    {
      id: '3',
      name: 'impl-1',
      role: 'Implementer',
      status: 'idle',
      output: [],
      model: 'claude-sonnet',
    },
  ]);
  const [selected, setSelected] = useState<string>('2');
  const [showAdd, setShowAdd] = useState(false);
  const [newRole, setNewRole] = useState(0);

  const toggleAgent = (id: string) => {
    setAgents((prev) =>
      prev.map((a) => {
        if (a.id !== id) return a;
        if (a.status === 'running') return { ...a, status: 'idle' as const };
        if (a.status === 'idle')
          return {
            ...a,
            status: 'running' as const,
            output: [...a.output, 'Starting task execution...'],
          };
        return a;
      })
    );
  };

  const addAgent = () => {
    const role = ROLES[newRole];
    const agent: Agent = {
      id: Date.now().toString(),
      name: `${role.name.toLowerCase().replace(' ', '-')}-${agents.length + 1}`,
      role: role.name,
      status: 'idle',
      output: [`Spawned as ${role.name}`, role.desc],
      model: 'claude-sonnet',
    };
    setAgents([...agents, agent]);
    setShowAdd(false);
  };

  const removeAgent = (id: string) => setAgents((prev) => prev.filter((a) => a.id !== id));

  useEffect(() => {
    const interval = setInterval(() => {
      setAgents((prev) =>
        prev.map((a) => {
          if (a.status !== 'running') return a;
          const messages = [
            'Reading file: src/components/App.tsx',
            'Analyzing dependencies...',
            'Writing test cases...',
            'Running lint checks...',
            'Generating documentation...',
            'Optimizing imports...',
            'Refactoring module...',
            'Committing changes...',
          ];
          if (a.output.length > 8)
            return { ...a, status: 'done', output: [...a.output, 'Task completed successfully'] };
          return {
            ...a,
            output: [...a.output, messages[Math.floor(Math.random() * messages.length)]],
          };
        })
      );
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const activeAgent = agents.find((a) => a.id === selected);
  const runningCount = agents.filter((a) => a.status === 'running').length;

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80">
      <div className="flex items-center justify-between px-3 py-2 border-b border-blue-500/10 bg-[#111d2e]">
        <div className="flex items-center gap-2">
          <Bot size={16} className="text-purple-400" />
          <span className="text-sm text-blue-200 font-semibold">Multi-Agent Terminal</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/15 text-purple-300">
            {runningCount} running
          </span>
        </div>
        <div className="flex gap-1">
          <button
            onClick={() => setShowAdd(!showAdd)}
            className="p-1.5 rounded hover:bg-blue-500/20 text-blue-400"
          >
            <Plus size={14} />
          </button>
          <button
            onClick={() => setAgents([])}
            className="p-1.5 rounded hover:bg-red-500/20 text-blue-300/40"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {showAdd && (
        <div className="flex items-center gap-2 px-3 py-2 border-b border-blue-500/10 bg-[#162032]">
          <select
            value={newRole}
            onChange={(e) => setNewRole(Number(e.target.value))}
            className="bg-[#0d1926] border border-blue-500/15 rounded px-2 py-1 text-xs outline-none"
          >
            {ROLES.map((r, i) => (
              <option key={i} value={i}>
                {r.name}
              </option>
            ))}
          </select>
          <button
            onClick={addAgent}
            className="px-3 py-1 rounded bg-blue-500/20 text-blue-200 text-xs hover:bg-blue-500/30"
          >
            Spawn
          </button>
        </div>
      )}

      <div className="flex flex-1 overflow-hidden">
        <div className="w-48 border-r border-blue-500/10 overflow-y-auto">
          {agents.map((a) => (
            <button
              key={a.id}
              onClick={() => setSelected(a.id)}
              className={`w-full text-left px-3 py-2 border-b border-blue-500/5 transition-colors ${selected === a.id ? 'bg-blue-500/10' : 'hover:bg-blue-500/5'}`}
            >
              <div className="flex items-center gap-2">
                {a.status === 'running' ? (
                  <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                ) : a.status === 'done' ? (
                  <CheckCircle size={12} className="text-blue-400" />
                ) : a.status === 'error' ? (
                  <XCircle size={12} className="text-red-400" />
                ) : (
                  <div className="w-2 h-2 rounded-full bg-blue-400/30" />
                )}
                <span className="text-xs text-blue-200/70 truncate">{a.name}</span>
              </div>
              <div className="text-[10px] text-blue-300/30 ml-4">{a.role}</div>
            </button>
          ))}
        </div>

        {activeAgent && (
          <div className="flex-1 flex flex-col overflow-hidden">
            <div className="flex items-center justify-between px-3 py-2 border-b border-blue-500/10">
              <div className="flex items-center gap-2">
                <Bot size={14} className="text-purple-400" />
                <span className="text-xs text-blue-200">{activeAgent.name}</span>
                <span className="text-[10px] text-blue-300/30">{activeAgent.model}</span>
              </div>
              <div className="flex gap-1">
                <button
                  onClick={() => toggleAgent(activeAgent.id)}
                  className={`p-1.5 rounded ${activeAgent.status === 'running' ? 'hover:bg-red-500/20 text-red-400' : 'hover:bg-green-500/20 text-green-400'}`}
                >
                  {activeAgent.status === 'running' ? <Square size={12} /> : <Play size={12} />}
                </button>
                <button
                  onClick={() => removeAgent(activeAgent.id)}
                  className="p-1.5 rounded hover:bg-red-500/20 text-blue-300/30"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-3 font-mono text-xs space-y-1">
              {activeAgent.output.map((line, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="text-blue-400/30 text-[10px] mt-0.5">
                    {String(i + 1).padStart(3, '0')}
                  </span>
                  <span className="text-green-400/70">{line}</span>
                </div>
              ))}
              {activeAgent.status === 'running' && (
                <div className="flex items-center gap-2 text-blue-400/40">
                  <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                  <span>Executing...</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
