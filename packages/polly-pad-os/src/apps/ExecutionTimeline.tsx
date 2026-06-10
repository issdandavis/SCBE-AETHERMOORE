import React, { useState, useEffect } from 'react';
import {
  Play,
  Square,
  RotateCcw,
  GitBranch,
  ArrowRight,
  Clock,
  CheckCircle,
  XCircle,
  Loader,
} from 'lucide-react';

interface Task {
  id: string;
  name: string;
  agent: string;
  status: 'pending' | 'running' | 'success' | 'failed' | 'retrying';
  startTime: string;
  duration: string;
  progress: number;
  dependencies: string[];
  output: string;
}

const INITIAL_TASKS: Task[] = [
  {
    id: 'T001',
    name: 'code_exploration',
    agent: 'explorer-alpha',
    status: 'success',
    startTime: '14:02:01',
    duration: '3.2s',
    progress: 100,
    dependencies: [],
    output: 'Indexed 847 files, 64 modules',
  },
  {
    id: 'T002',
    name: 'dependency_analysis',
    agent: 'explorer-alpha',
    status: 'success',
    startTime: '14:02:05',
    duration: '1.8s',
    progress: 100,
    dependencies: ['T001'],
    output: 'Found 34 deps, 2 vulnerable',
  },
  {
    id: 'T003',
    name: 'architecture_design',
    agent: 'architect-beta',
    status: 'success',
    startTime: '14:02:08',
    duration: '5.4s',
    progress: 100,
    dependencies: ['T002'],
    output: 'Generated API contracts, 12 endpoints',
  },
  {
    id: 'T004',
    name: 'security_review',
    agent: 'review-delta',
    status: 'running',
    startTime: '14:02:15',
    duration: '--',
    progress: 65,
    dependencies: ['T003'],
    output: 'Scanning auth module... 12/18 files',
  },
  {
    id: 'T005',
    name: 'implementation',
    agent: 'impl-gamma',
    status: 'pending',
    startTime: '--',
    duration: '--',
    progress: 0,
    dependencies: ['T004'],
    output: 'Waiting for approval...',
  },
  {
    id: 'T006',
    name: 'test_generation',
    agent: 'impl-gamma',
    status: 'pending',
    startTime: '--',
    duration: '--',
    progress: 0,
    dependencies: ['T005'],
    output: 'Queued',
  },
  {
    id: 'T007',
    name: 'integration_test',
    agent: 'review-delta',
    status: 'pending',
    startTime: '--',
    duration: '--',
    progress: 0,
    dependencies: ['T006'],
    output: 'Queued',
  },
  {
    id: 'T008',
    name: 'deployment_prep',
    agent: 'security-epsilon',
    status: 'pending',
    startTime: '--',
    duration: '--',
    progress: 0,
    dependencies: ['T007'],
    output: 'Queued',
  },
];

const STATUS_CONFIG: Record<string, { color: string; icon: React.ReactNode; bg: string }> = {
  pending: { color: 'text-blue-300/30', icon: <Clock size={12} />, bg: 'bg-blue-500/5' },
  running: {
    color: 'text-blue-400',
    icon: <Loader size={12} className="animate-spin" />,
    bg: 'bg-blue-500/10',
  },
  success: { color: 'text-green-400', icon: <CheckCircle size={12} />, bg: 'bg-green-500/10' },
  failed: { color: 'text-red-400', icon: <XCircle size={12} />, bg: 'bg-red-500/10' },
  retrying: {
    color: 'text-yellow-400',
    icon: <RotateCcw size={12} className="animate-spin" />,
    bg: 'bg-yellow-500/10',
  },
};

export default function ExecutionTimeline() {
  const [tasks, setTasks] = useState(INITIAL_TASKS);
  const [selectedTask, setSelectedTask] = useState<string>('T004');
  const [isRunning, setIsRunning] = useState(true);

  useEffect(() => {
    if (!isRunning) return;
    const interval = setInterval(() => {
      setTasks((prev) =>
        prev.map((t) => {
          if (t.status === 'running') {
            const newProgress = Math.min(100, t.progress + Math.random() * 15);
            if (newProgress >= 100)
              return {
                ...t,
                status: 'success' as const,
                progress: 100,
                duration: `${(Math.random() * 5 + 2).toFixed(1)}s`,
              };
            return { ...t, progress: Math.round(newProgress) };
          }
          if (t.status === 'pending') {
            const depsDone = t.dependencies.every(
              (d) => prev.find((x) => x.id === d)?.status === 'success'
            );
            if (depsDone)
              return {
                ...t,
                status: 'running' as const,
                startTime: new Date().toLocaleTimeString('en', { hour12: false }),
                progress: 5,
                output: 'Starting execution...',
              };
          }
          return t;
        })
      );
    }, 1500);
    return () => clearInterval(interval);
  }, [isRunning]);

  const activeTask = tasks.find((t) => t.id === selectedTask);

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80">
      <div className="flex items-center justify-between px-4 py-3 border-b border-blue-500/10 bg-[#111d2e]">
        <div className="flex items-center gap-2">
          <GitBranch size={18} className="text-blue-400" />
          <h2 className="text-sm font-semibold text-blue-200">Execution Timeline</h2>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsRunning(!isRunning)}
            className={`p-1.5 rounded ${isRunning ? 'hover:bg-red-500/20 text-red-400' : 'hover:bg-green-500/20 text-green-400'}`}
          >
            {isRunning ? <Square size={14} /> : <Play size={14} />}
          </button>
          <span className="text-[10px] px-2 py-1 rounded bg-blue-500/10 text-blue-300">
            {tasks.filter((t) => t.status === 'success').length}/{tasks.length} done
          </span>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Task List */}
        <div className="w-72 border-r border-blue-500/10 overflow-y-auto">
          <div className="p-2">
            {/* DAG-style connectors */}
            <div className="space-y-0">
              {tasks.map((task, idx) => {
                const cfg = STATUS_CONFIG[task.status];
                return (
                  <div key={task.id}>
                    {idx > 0 && (
                      <div className="flex items-center gap-1 ml-3 h-4">
                        <div className="w-0.5 h-full bg-blue-500/10" />
                        <ArrowRight size={8} className="text-blue-500/20" />
                      </div>
                    )}
                    <button
                      onClick={() => setSelectedTask(task.id)}
                      className={`w-full text-left p-2.5 rounded-xl transition-colors ${selectedTask === task.id ? 'bg-blue-500/10 border border-blue-500/20' : 'hover:bg-blue-500/5 border border-transparent'} ${cfg.bg}`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span className={cfg.color}>{cfg.icon}</span>
                        <span className="text-xs text-blue-200/70 font-mono">{task.name}</span>
                        <span className="text-[9px] text-blue-300/20 ml-auto">{task.agent}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1 bg-blue-500/5 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{
                              width: `${task.progress}%`,
                              background:
                                task.status === 'success'
                                  ? '#4ade80'
                                  : task.status === 'failed'
                                    ? '#ef4444'
                                    : '#3b82f6',
                            }}
                          />
                        </div>
                        <span className="text-[9px] text-blue-300/30 w-8 text-right">
                          {task.progress}%
                        </span>
                      </div>
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Detail Panel */}
        {activeTask && (
          <div className="flex-1 p-4 overflow-y-auto">
            <div className="bg-[#162032] rounded-xl p-4 border border-blue-500/10">
              <div className="flex items-center gap-3 mb-4">
                {STATUS_CONFIG[activeTask.status].icon}
                <div>
                  <div className="text-sm text-blue-200 font-semibold font-mono">
                    {activeTask.name}
                  </div>
                  <div className="text-[10px] text-blue-300/30">
                    Agent: {activeTask.agent} | Started: {activeTask.startTime}
                  </div>
                </div>
                <span
                  className={`ml-auto px-2 py-0.5 rounded text-[10px] ${STATUS_CONFIG[activeTask.status].color} ${STATUS_CONFIG[activeTask.status].bg}`}
                >
                  {activeTask.status}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-2 mb-4">
                <div className="bg-[#0d1926] rounded-lg p-2 text-center">
                  <div className="text-[10px] text-blue-300/20">Progress</div>
                  <div className="text-sm text-blue-200">{activeTask.progress}%</div>
                </div>
                <div className="bg-[#0d1926] rounded-lg p-2 text-center">
                  <div className="text-[10px] text-blue-300/20">Duration</div>
                  <div className="text-sm text-blue-200">{activeTask.duration}</div>
                </div>
                <div className="bg-[#0d1926] rounded-lg p-2 text-center">
                  <div className="text-[10px] text-blue-300/20">Dependencies</div>
                  <div className="text-sm text-blue-200">{activeTask.dependencies.length}</div>
                </div>
              </div>

              <div className="bg-[#0d1926] rounded-lg p-3 font-mono text-xs text-green-400/70 min-h-[100px]">
                {activeTask.output}
                {activeTask.status === 'running' && <span className="animate-pulse">_</span>}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
