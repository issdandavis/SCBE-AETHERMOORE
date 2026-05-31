import React, { useMemo, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Crosshair,
  Radio,
  Shield,
  ShieldAlert,
  Target,
  Users,
  Zap,
} from 'lucide-react';
import { useOverseerTelemetry } from '../../lib/scbe-bridge';

type AlertLevel = 'critical' | 'high' | 'medium';
type TaskState = 'queued' | 'executing' | 'review' | 'blocked' | 'done';

interface OpsAlert {
  id: string;
  level: AlertLevel;
  lane: string;
  message: string;
  time: string;
}

interface MissionTask {
  id: string;
  title: string;
  lane: string;
  owner: string;
  state: TaskState;
}

const STATE_COLOR: Record<TaskState, string> = {
  queued: 'text-zinc-400',
  executing: 'text-cyan-400',
  review: 'text-amber-400',
  blocked: 'text-red-400',
  done: 'text-emerald-400',
};

const ALERT_COLOR: Record<AlertLevel, string> = {
  critical: 'border-red-500/60 bg-red-500/10',
  high: 'border-amber-500/60 bg-amber-500/10',
  medium: 'border-blue-500/60 bg-blue-500/10',
};

export const OverseerControlPanelApp: React.FC = () => {
  const { telemetry } = useOverseerTelemetry();
  const alerts = telemetry.alerts as OpsAlert[];
  const tasks = telemetry.tasks as MissionTask[];
  const [selectedLane, setSelectedLane] = useState<string>('all');

  const lanes = useMemo(() => ['all', ...Array.from(new Set(tasks.map((t) => t.lane)))], [tasks]);
  const visibleTasks = useMemo(
    () => (selectedLane === 'all' ? tasks : tasks.filter((t) => t.lane === selectedLane)),
    [selectedLane, tasks],
  );

  const executing = tasks.filter((t) => t.state === 'executing').length;
  const review = tasks.filter((t) => t.state === 'review').length;
  const blocked = tasks.filter((t) => t.state === 'blocked').length;

  return (
    <div className="h-full w-full bg-zinc-950 text-white flex flex-col">
      <div className="p-4 border-b border-zinc-800 bg-zinc-900/80">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-fuchsia-500 flex items-center justify-center">
              <Crosshair size={18} />
            </div>
            <div>
              <h2 className="text-lg font-black">Overseer Control Panel</h2>
              <p className="text-xs text-zinc-400">RTS-inspired mission control for agentic execution</p>
            </div>
          </div>
          <div className="text-[10px] uppercase tracking-widest text-zinc-500 flex items-center gap-2">
            <Radio size={12} className="text-emerald-400" />
            Control Plane Live
          </div>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-3 p-4 border-b border-zinc-900">
        <div className="rounded-xl bg-zinc-900 p-3 border border-zinc-800">
          <div className="text-[10px] uppercase text-zinc-500">Agents Online</div>
          <div className="text-2xl font-black mt-1 flex items-center gap-2">
            <Users size={16} className="text-cyan-400" /> {telemetry.agentsOnline}
          </div>
        </div>
        <div className="rounded-xl bg-zinc-900 p-3 border border-zinc-800">
          <div className="text-[10px] uppercase text-zinc-500">Executing</div>
          <div className="text-2xl font-black mt-1 text-cyan-400">{executing}</div>
        </div>
        <div className="rounded-xl bg-zinc-900 p-3 border border-zinc-800">
          <div className="text-[10px] uppercase text-zinc-500">Review Gate</div>
          <div className="text-2xl font-black mt-1 text-amber-400">{review}</div>
        </div>
        <div className="rounded-xl bg-zinc-900 p-3 border border-zinc-800">
          <div className="text-[10px] uppercase text-zinc-500">Blocked</div>
          <div className="text-2xl font-black mt-1 text-red-400">{blocked}</div>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="w-[42%] border-r border-zinc-900 p-4 overflow-auto">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Alert Feed</h3>
            <span className="text-[10px] text-zinc-500">{alerts.length} active</span>
          </div>
          <div className="space-y-2 mb-6">
            {alerts.map((alert) => (
              <div key={alert.id} className={`rounded-xl border p-3 ${ALERT_COLOR[alert.level]}`}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] uppercase tracking-widest">{alert.level}</span>
                  <span className="text-[10px] text-zinc-400">{alert.time}</span>
                </div>
                <div className="text-sm font-semibold">{alert.message}</div>
                <div className="text-[11px] mt-1 text-zinc-400">lane: {alert.lane}</div>
              </div>
            ))}
          </div>

          <h3 className="text-xs uppercase tracking-widest text-zinc-500 font-bold mb-3">Doctrine Switches</h3>
          <div className="grid grid-cols-1 gap-2">
            <div className="rounded-lg bg-zinc-900 border border-zinc-800 p-3 flex items-center justify-between">
              <span className="text-sm">Execution Layer</span>
              <Zap size={14} className="text-cyan-400" />
            </div>
            <div className="rounded-lg bg-zinc-900 border border-zinc-800 p-3 flex items-center justify-between">
              <span className="text-sm">Review Layer</span>
              <Shield size={14} className="text-amber-400" />
            </div>
            <div className="rounded-lg bg-zinc-900 border border-zinc-800 p-3 flex items-center justify-between">
              <span className="text-sm">Temporal Reliance</span>
              <Clock3 size={14} className="text-blue-400" />
            </div>
          </div>
        </div>

        <div className="flex-1 p-4 overflow-auto">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Mission Queue</h3>
            <div className="flex gap-1">
              {lanes.map((lane) => (
                <button
                  key={lane}
                  onClick={() => setSelectedLane(lane)}
                  className={`px-2 py-1 rounded text-[10px] uppercase tracking-widest ${
                    selectedLane === lane ? 'bg-cyan-600 text-white' : 'bg-zinc-900 text-zinc-400'
                  }`}
                >
                  {lane}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            {visibleTasks.map((task) => (
              <div key={task.id} className="rounded-xl border border-zinc-800 bg-zinc-900 p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-sm">{task.title}</div>
                    <div className="text-[11px] text-zinc-400 mt-1">
                      {task.owner} · lane: {task.lane}
                    </div>
                  </div>
                  <div className={`text-[10px] uppercase tracking-widest font-bold ${STATE_COLOR[task.state]}`}>
                    {task.state}
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-5 rounded-xl border border-zinc-800 bg-black/40 p-3">
            <div className="text-xs uppercase tracking-widest text-zinc-500 mb-2">Battle Board</div>
            <div className="grid grid-cols-3 gap-2 text-[11px]">
              <div className="rounded-lg bg-zinc-900 p-2 border border-zinc-800 flex items-center gap-2">
                <Target size={12} className="text-cyan-400" />
                Prioritize highest-risk queue first
              </div>
              <div className="rounded-lg bg-zinc-900 p-2 border border-zinc-800 flex items-center gap-2">
                <ShieldAlert size={12} className="text-amber-400" />
                Escalate when review confidence drops
              </div>
              <div className="rounded-lg bg-zinc-900 p-2 border border-zinc-800 flex items-center gap-2">
                <CheckCircle2 size={12} className="text-emerald-400" />
                Commit only after Stage6 + review
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="px-4 py-2 border-t border-zinc-900 text-[10px] uppercase tracking-widest text-zinc-500 flex items-center justify-between">
        <span>StarCraft pattern: control groups + alerts + camera jumps</span>
        <span>AI Ops pattern: traces + hypotheses + gated actions</span>
      </div>
    </div>
  );
};
