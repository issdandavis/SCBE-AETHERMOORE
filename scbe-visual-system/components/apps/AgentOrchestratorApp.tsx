/**
 * Agent Orchestrator App - Multi-Headed AI Agent Control
 *
 * Enterprise-grade multi-agent orchestration with specialized roles:
 * - Orchestrator (DR): High-level steering and task distribution
 * - Navigator (CA): Context reading, maps, and decision logic
 * - Executor (AV): Code execution and I/O operations
 *
 * @license Apache-2.0
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Brain, Map, Code2, Play, Pause, RotateCcw, Plus,
  ArrowRight, CheckCircle, Clock, AlertTriangle, Zap,
  Network, GitBranch, Settings, Terminal, Eye
} from 'lucide-react';

// Agent role definitions (mapped to Sacred Tongue governance)
const AGENT_ROLES = {
  ORCHESTRATOR: {
    id: 'orchestrator',
    name: 'Orchestrator',
    tongue: 'DR',
    icon: Brain,
    color: 'bg-red-500',
    description: 'High-level steering, task distribution, architectural decisions',
    capabilities: ['task_decomposition', 'agent_coordination', 'priority_management']
  },
  NAVIGATOR: {
    id: 'navigator',
    name: 'Navigator',
    tongue: 'CA',
    icon: Map,
    color: 'bg-green-500',
    description: 'Context reading, decision logic, path planning',
    capabilities: ['context_analysis', 'decision_trees', 'knowledge_retrieval']
  },
  EXECUTOR: {
    id: 'executor',
    name: 'Executor',
    tongue: 'AV',
    icon: Code2,
    color: 'bg-blue-500',
    description: 'Code execution, I/O operations, tool invocation',
    capabilities: ['code_execution', 'api_calls', 'file_operations']
  }
};

interface Task {
  id: string;
  title: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  assignedTo: string[];
  progress: number;
  logs: string[];
  createdAt: Date;
}

interface AgentState {
  id: string;
  role: keyof typeof AGENT_ROLES;
  status: 'idle' | 'working' | 'waiting';
  currentTask?: string;
  load: number;
}

export const AgentOrchestratorApp: React.FC = () => {
  const [agents, setAgents] = useState<AgentState[]>([
    { id: 'orch-1', role: 'ORCHESTRATOR', status: 'idle', load: 0 },
    { id: 'nav-1', role: 'NAVIGATOR', status: 'idle', load: 0 },
    { id: 'exec-1', role: 'EXECUTOR', status: 'idle', load: 0 }
  ]);

  const [tasks, setTasks] = useState<Task[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([
    '[SYSTEM] Multi-agent orchestrator initialized',
    '[SYSTEM] 3 agents online: Orchestrator, Navigator, Executor',
    '[SYSTEM] Ready for task submission'
  ]);

  // Simulate task execution flow
  const executeTask = useCallback((task: Task) => {
    const addLog = (msg: string) => {
      setLogs(prev => [...prev.slice(-50), `[${new Date().toLocaleTimeString()}] ${msg}`]);
    };

    // Phase 1: Orchestrator decomposes task
    addLog(`[ORCHESTRATOR] Received task: "${task.title}"`);
    setAgents(prev => prev.map(a =>
      a.role === 'ORCHESTRATOR' ? { ...a, status: 'working', currentTask: task.id, load: 80 } : a
    ));

    setTimeout(() => {
      addLog(`[ORCHESTRATOR] Task decomposed into subtasks`);
      addLog(`[ORCHESTRATOR] Assigning context analysis to Navigator`);

      // Phase 2: Navigator analyzes context
      setAgents(prev => prev.map(a => {
        if (a.role === 'ORCHESTRATOR') return { ...a, status: 'waiting', load: 30 };
        if (a.role === 'NAVIGATOR') return { ...a, status: 'working', currentTask: task.id, load: 90 };
        return a;
      }));

      setTimeout(() => {
        addLog(`[NAVIGATOR] Analyzing context and dependencies`);
        addLog(`[NAVIGATOR] Building execution plan`);
        addLog(`[NAVIGATOR] Handing off to Executor`);

        // Phase 3: Executor runs the code
        setAgents(prev => prev.map(a => {
          if (a.role === 'NAVIGATOR') return { ...a, status: 'waiting', load: 20 };
          if (a.role === 'EXECUTOR') return { ...a, status: 'working', currentTask: task.id, load: 95 };
          return a;
        }));

        setTimeout(() => {
          addLog(`[EXECUTOR] Executing task operations`);
          addLog(`[EXECUTOR] Running secure code sandbox`);

          setTimeout(() => {
            addLog(`[EXECUTOR] Task completed successfully`);
            addLog(`[ORCHESTRATOR] Verifying results`);

            // Complete
            setTasks(prev => prev.map(t =>
              t.id === task.id ? { ...t, status: 'completed', progress: 100 } : t
            ));
            setAgents(prev => prev.map(a => ({ ...a, status: 'idle', currentTask: undefined, load: 0 })));
            addLog(`[SYSTEM] Task "${task.title}" completed`);
          }, 1500);
        }, 2000);
      }, 2000);
    }, 1500);
  }, []);

  const addTask = () => {
    if (!newTaskTitle.trim()) return;

    const task: Task = {
      id: `task-${Date.now()}`,
      title: newTaskTitle.trim(),
      status: 'pending',
      assignedTo: ['orchestrator', 'navigator', 'executor'],
      progress: 0,
      logs: [],
      createdAt: new Date()
    };

    setTasks(prev => [...prev, task]);
    setNewTaskTitle('');

    if (isRunning) {
      task.status = 'running';
      executeTask(task);
    }
  };

  const startOrchestration = () => {
    setIsRunning(true);
    setLogs(prev => [...prev, '[SYSTEM] Orchestration started']);

    // Start any pending tasks
    const pendingTask = tasks.find(t => t.status === 'pending');
    if (pendingTask) {
      setTasks(prev => prev.map(t =>
        t.id === pendingTask.id ? { ...t, status: 'running' } : t
      ));
      executeTask(pendingTask);
    }
  };

  const stopOrchestration = () => {
    setIsRunning(false);
    setLogs(prev => [...prev, '[SYSTEM] Orchestration paused']);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'working': return <Zap size={12} className="text-yellow-400 animate-pulse" />;
      case 'waiting': return <Clock size={12} className="text-blue-400" />;
      default: return <CheckCircle size={12} className="text-zinc-500" />;
    }
  };

  return (
    <div className="h-full w-full bg-zinc-900 flex flex-col text-white overflow-hidden">
      {/* Header */}
      <div className="p-4 bg-zinc-800 border-b border-zinc-700">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-red-500 via-green-500 to-blue-500 flex items-center justify-center">
              <Network size={20} />
            </div>
            <div>
              <h2 className="font-black text-lg">Agent Orchestrator</h2>
              <div className="text-xs text-zinc-400">Multi-Headed AI Coordination System</div>
            </div>
          </div>
          <div className="flex gap-2">
            {isRunning ? (
              <button
                onClick={stopOrchestration}
                className="px-4 py-2 bg-yellow-600 rounded-lg text-xs font-bold uppercase tracking-widest flex items-center gap-2 hover:bg-yellow-500"
              >
                <Pause size={14} /> Pause
              </button>
            ) : (
              <button
                onClick={startOrchestration}
                className="px-4 py-2 bg-emerald-600 rounded-lg text-xs font-bold uppercase tracking-widest flex items-center gap-2 hover:bg-emerald-500"
              >
                <Play size={14} /> Start
              </button>
            )}
          </div>
        </div>

        {/* Agent Status Bar */}
        <div className="flex gap-3">
          {agents.map(agent => {
            const role = AGENT_ROLES[agent.role];
            const Icon = role.icon;
            return (
              <div
                key={agent.id}
                onClick={() => setSelectedAgent(agent.id)}
                className={`flex-1 p-3 rounded-xl cursor-pointer transition-all ${
                  selectedAgent === agent.id ? 'ring-2 ring-white' : ''
                } ${role.color}/20 border border-${role.color.replace('bg-', '')}/30`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Icon size={16} className={role.color.replace('bg-', 'text-').replace('-500', '-400')} />
                    <span className="font-bold text-sm">{role.name}</span>
                  </div>
                  {getStatusIcon(agent.status)}
                </div>
                <div className="text-[10px] text-zinc-500 uppercase mb-2">{role.tongue} Tier</div>
                <div className="h-1 bg-zinc-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${role.color} transition-all duration-500`}
                    style={{ width: `${agent.load}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Task Queue */}
        <div className="w-1/2 border-r border-zinc-700 flex flex-col">
          <div className="p-3 border-b border-zinc-700 bg-zinc-800/50">
            <div className="flex gap-2">
              <input
                type="text"
                value={newTaskTitle}
                onChange={(e) => setNewTaskTitle(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addTask()}
                placeholder="Enter new task..."
                className="flex-1 bg-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
              <button
                onClick={addTask}
                disabled={!newTaskTitle.trim()}
                className="px-4 py-2 bg-emerald-600 rounded-lg disabled:opacity-50 hover:bg-emerald-500"
              >
                <Plus size={16} />
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-auto p-3 space-y-2">
            <h3 className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-2">
              Task Queue ({tasks.length})
            </h3>
            {tasks.length === 0 ? (
              <div className="text-center text-zinc-500 py-8">
                <GitBranch size={32} className="mx-auto mb-2 opacity-50" />
                <p className="text-sm">No tasks queued</p>
                <p className="text-xs">Add a task to see multi-agent orchestration</p>
              </div>
            ) : (
              tasks.map(task => (
                <div
                  key={task.id}
                  className={`bg-zinc-800 rounded-xl p-3 border-l-4 ${
                    task.status === 'completed' ? 'border-emerald-500' :
                    task.status === 'running' ? 'border-yellow-500' :
                    task.status === 'failed' ? 'border-red-500' : 'border-zinc-600'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-bold text-sm">{task.title}</span>
                    <span className={`text-[10px] uppercase font-bold ${
                      task.status === 'completed' ? 'text-emerald-400' :
                      task.status === 'running' ? 'text-yellow-400' :
                      task.status === 'failed' ? 'text-red-400' : 'text-zinc-500'
                    }`}>
                      {task.status}
                    </span>
                  </div>
                  <div className="h-1 bg-zinc-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 ${
                        task.status === 'completed' ? 'bg-emerald-500' :
                        task.status === 'running' ? 'bg-yellow-500' : 'bg-zinc-600'
                      }`}
                      style={{ width: `${task.progress}%` }}
                    />
                  </div>
                  <div className="flex gap-1 mt-2">
                    {task.assignedTo.map(role => (
                      <span key={role} className="px-1.5 py-0.5 bg-zinc-700 rounded text-[9px] uppercase">
                        {role.slice(0, 4)}
                      </span>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Execution Log */}
        <div className="w-1/2 flex flex-col">
          <div className="p-3 border-b border-zinc-700 bg-zinc-800/50 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Terminal size={14} className="text-zinc-500" />
              <span className="text-xs font-bold uppercase tracking-widest text-zinc-500">Execution Log</span>
            </div>
            <button
              onClick={() => setLogs([])}
              className="p-1 hover:bg-zinc-700 rounded"
            >
              <RotateCcw size={12} />
            </button>
          </div>
          <div className="flex-1 overflow-auto p-3 font-mono text-xs bg-black/30">
            {logs.map((log, i) => (
              <div
                key={i}
                className={`mb-1 ${
                  log.includes('[ORCHESTRATOR]') ? 'text-red-400' :
                  log.includes('[NAVIGATOR]') ? 'text-green-400' :
                  log.includes('[EXECUTOR]') ? 'text-blue-400' :
                  'text-zinc-500'
                }`}
              >
                {log}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Footer - Architecture Diagram */}
      <div className="p-3 bg-zinc-800 border-t border-zinc-700">
        <div className="flex items-center justify-center gap-4 text-[10px]">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-red-500/20 flex items-center justify-center">
              <Brain size={12} className="text-red-400" />
            </div>
            <span className="text-zinc-400">Orchestrator (DR)</span>
          </div>
          <ArrowRight size={12} className="text-zinc-600" />
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-green-500/20 flex items-center justify-center">
              <Map size={12} className="text-green-400" />
            </div>
            <span className="text-zinc-400">Navigator (CA)</span>
          </div>
          <ArrowRight size={12} className="text-zinc-600" />
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-blue-500/20 flex items-center justify-center">
              <Code2 size={12} className="text-blue-400" />
            </div>
            <span className="text-zinc-400">Executor (AV)</span>
          </div>
        </div>
      </div>
    </div>
  );
};
