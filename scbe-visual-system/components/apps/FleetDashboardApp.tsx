/**
 * Fleet Dashboard App - AI Agent Fleet Management
 *
 * Monitor and manage distributed AI agents with SCBE security,
 * view swarm status, and coordinate multi-agent operations.
 *
 * @license Apache-2.0
 */
import React, { useState, useEffect } from 'react';
import {
  Users, Activity, Shield, Wifi, WifiOff, AlertTriangle,
  CheckCircle, XCircle, Clock, Zap, BarChart3, Radio,
  Plus, RefreshCw, Settings, Eye
} from 'lucide-react';
import { useSCBEBridge, FleetAgent, GovernanceTier, TIER_THRESHOLDS } from '../../lib/scbe-bridge';

const TIER_COLORS: Record<GovernanceTier, string> = {
  'KO': 'bg-pink-500',
  'AV': 'bg-blue-500',
  'RU': 'bg-yellow-500',
  'CA': 'bg-green-500',
  'UM': 'bg-purple-500',
  'DR': 'bg-red-500'
};

const STATUS_ICONS: Record<string, React.FC<{ size: number; className?: string }>> = {
  'online': CheckCircle,
  'offline': WifiOff,
  'busy': Clock,
  'error': XCircle
};

const STATUS_COLORS: Record<string, string> = {
  'online': 'text-emerald-400',
  'offline': 'text-zinc-500',
  'busy': 'text-yellow-400',
  'error': 'text-red-400'
};

export const FleetDashboardApp: React.FC = () => {
  const { bridge, agents, pads, refresh } = useSCBEBridge();
  const [selectedAgent, setSelectedAgent] = useState<FleetAgent | null>(null);
  const [view, setView] = useState<'grid' | 'list'>('grid');
  const [newAgentName, setNewAgentName] = useState('');
  const [showAddAgent, setShowAddAgent] = useState(false);

  const swarmStatus = bridge.getSwarmStatus();

  const handleAddAgent = () => {
    if (newAgentName.trim()) {
      bridge.registerAgent(newAgentName.trim(), ['general']);
      setNewAgentName('');
      setShowAddAgent(false);
      refresh();
    }
  };

  return (
    <div className="h-full w-full bg-zinc-900 flex flex-col text-white">
      {/* Header */}
      <div className="p-4 bg-zinc-800 border-b border-zinc-700">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center">
              <Users size={20} />
            </div>
            <div>
              <h2 className="font-black text-lg">Fleet Dashboard</h2>
              <div className="text-xs text-zinc-400">SCBE-Secured Agent Management</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={refresh}
              className="p-2 bg-zinc-700 rounded-lg hover:bg-zinc-600 transition-colors"
            >
              <RefreshCw size={16} />
            </button>
            <button
              onClick={() => setShowAddAgent(true)}
              className="px-4 py-2 bg-indigo-600 rounded-lg text-xs font-bold uppercase tracking-widest flex items-center gap-2 hover:bg-indigo-500"
            >
              <Plus size={14} /> Add Agent
            </button>
          </div>
        </div>

        {/* Swarm Stats */}
        <div className="grid grid-cols-4 gap-3">
          <div className="bg-zinc-700/50 rounded-lg p-3 text-center">
            <div className="text-2xl font-black">{swarmStatus.totalAgents}</div>
            <div className="text-[10px] text-zinc-400 uppercase tracking-widest">Total Agents</div>
          </div>
          <div className="bg-zinc-700/50 rounded-lg p-3 text-center">
            <div className="text-2xl font-black text-emerald-400">{swarmStatus.onlineAgents}</div>
            <div className="text-[10px] text-zinc-400 uppercase tracking-widest">Online</div>
          </div>
          <div className="bg-zinc-700/50 rounded-lg p-3 text-center">
            <div className="text-2xl font-black text-sky-400">{(swarmStatus.avgCoherence * 100).toFixed(0)}%</div>
            <div className="text-[10px] text-zinc-400 uppercase tracking-widest">Coherence</div>
          </div>
          <div className="bg-zinc-700/50 rounded-lg p-3 text-center">
            <div className="text-2xl font-black text-purple-400">{(swarmStatus.avgNu * 100).toFixed(0)}%</div>
            <div className="text-[10px] text-zinc-400 uppercase tracking-widest">Avg Flux</div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Agent List */}
        <div className="flex-1 overflow-auto p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-sm uppercase tracking-widest text-zinc-400">
              Active Agents ({agents.length})
            </h3>
            <div className="flex gap-1">
              <button
                onClick={() => setView('grid')}
                className={`p-2 rounded ${view === 'grid' ? 'bg-zinc-700' : 'hover:bg-zinc-800'}`}
              >
                <BarChart3 size={14} />
              </button>
              <button
                onClick={() => setView('list')}
                className={`p-2 rounded ${view === 'list' ? 'bg-zinc-700' : 'hover:bg-zinc-800'}`}
              >
                <Activity size={14} />
              </button>
            </div>
          </div>

          {view === 'grid' ? (
            <div className="grid grid-cols-2 gap-3">
              {agents.map(agent => {
                const StatusIcon = STATUS_ICONS[agent.status];
                return (
                  <div
                    key={agent.id}
                    onClick={() => setSelectedAgent(agent)}
                    className={`bg-zinc-800 rounded-xl p-4 cursor-pointer transition-all hover:bg-zinc-750 border-2 ${
                      selectedAgent?.id === agent.id ? 'border-indigo-500' : 'border-transparent'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <div className={`w-8 h-8 rounded-lg ${TIER_COLORS[agent.tier]} flex items-center justify-center text-xs font-bold`}>
                          {agent.tier}
                        </div>
                        <div>
                          <div className="font-bold text-sm">{agent.name}</div>
                          <div className="text-[10px] text-zinc-500">{TIER_THRESHOLDS[agent.tier].name}</div>
                        </div>
                      </div>
                      <StatusIcon size={16} className={STATUS_COLORS[agent.status]} />
                    </div>

                    {agent.pad && (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <Activity size={12} className="text-zinc-500" />
                          <div className="flex-1 h-1.5 bg-zinc-700 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${
                                agent.pad.nu >= 0.8 ? 'bg-emerald-400' :
                                agent.pad.nu >= 0.5 ? 'bg-yellow-400' :
                                agent.pad.nu >= 0.1 ? 'bg-orange-400' : 'bg-red-400'
                              }`}
                              style={{ width: `${agent.pad.nu * 100}%` }}
                            />
                          </div>
                          <span className="text-[10px] font-mono text-zinc-500">{agent.pad.nu.toFixed(2)}</span>
                        </div>
                        <div className="flex items-center justify-between text-[10px] text-zinc-500">
                          <span>{agent.pad.dimensionalState}</span>
                          <span>{agent.pad.xp} XP</span>
                        </div>
                      </div>
                    )}

                    <div className="flex flex-wrap gap-1 mt-3">
                      {agent.capabilities.slice(0, 3).map(cap => (
                        <span key={cap} className="px-2 py-0.5 bg-zinc-700 rounded text-[10px]">
                          {cap}
                        </span>
                      ))}
                      {agent.capabilities.length > 3 && (
                        <span className="px-2 py-0.5 bg-zinc-700 rounded text-[10px]">
                          +{agent.capabilities.length - 3}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="space-y-2">
              {agents.map(agent => {
                const StatusIcon = STATUS_ICONS[agent.status];
                return (
                  <div
                    key={agent.id}
                    onClick={() => setSelectedAgent(agent)}
                    className={`bg-zinc-800 rounded-xl p-3 cursor-pointer transition-all hover:bg-zinc-750 border-2 flex items-center gap-4 ${
                      selectedAgent?.id === agent.id ? 'border-indigo-500' : 'border-transparent'
                    }`}
                  >
                    <div className={`w-10 h-10 rounded-lg ${TIER_COLORS[agent.tier]} flex items-center justify-center text-sm font-bold`}>
                      {agent.tier}
                    </div>
                    <div className="flex-1">
                      <div className="font-bold">{agent.name}</div>
                      <div className="text-xs text-zinc-500">
                        {TIER_THRESHOLDS[agent.tier].name} | {agent.capabilities.join(', ')}
                      </div>
                    </div>
                    {agent.pad && (
                      <div className="text-right">
                        <div className={`text-sm font-bold ${
                          agent.pad.dimensionalState === 'POLLY' ? 'text-emerald-400' :
                          agent.pad.dimensionalState === 'QUASI' ? 'text-yellow-400' :
                          agent.pad.dimensionalState === 'DEMI' ? 'text-orange-400' : 'text-red-400'
                        }`}>
                          {agent.pad.dimensionalState}
                        </div>
                        <div className="text-[10px] text-zinc-500">{agent.pad.xp} XP</div>
                      </div>
                    )}
                    <StatusIcon size={20} className={STATUS_COLORS[agent.status]} />
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Agent Detail Panel */}
        {selectedAgent && (
          <div className="w-80 bg-zinc-800 border-l border-zinc-700 p-4 overflow-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold">Agent Details</h3>
              <button
                onClick={() => setSelectedAgent(null)}
                className="p-1 hover:bg-zinc-700 rounded"
              >
                <XCircle size={16} />
              </button>
            </div>

            <div className="space-y-4">
              {/* Agent Info */}
              <div className="text-center">
                <div className={`w-16 h-16 rounded-xl ${TIER_COLORS[selectedAgent.tier]} flex items-center justify-center text-2xl font-bold mx-auto mb-2`}>
                  {selectedAgent.tier}
                </div>
                <h4 className="font-black text-lg">{selectedAgent.name}</h4>
                <div className="text-sm text-zinc-400">{TIER_THRESHOLDS[selectedAgent.tier].name}</div>
              </div>

              {/* Status */}
              <div className="bg-zinc-700/50 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-zinc-400">Status</span>
                  <span className={`flex items-center gap-1 ${STATUS_COLORS[selectedAgent.status]}`}>
                    {React.createElement(STATUS_ICONS[selectedAgent.status], { size: 14 })}
                    {selectedAgent.status.toUpperCase()}
                  </span>
                </div>
              </div>

              {/* Pad Info */}
              {selectedAgent.pad && (
                <>
                  <div className="bg-zinc-700/50 rounded-lg p-3 space-y-3">
                    <h5 className="font-bold text-sm">Polly Pad</h5>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-zinc-400">Dimensional State</span>
                      <span className={`font-bold ${
                        selectedAgent.pad.dimensionalState === 'POLLY' ? 'text-emerald-400' :
                        selectedAgent.pad.dimensionalState === 'QUASI' ? 'text-yellow-400' :
                        selectedAgent.pad.dimensionalState === 'DEMI' ? 'text-orange-400' : 'text-red-400'
                      }`}>
                        {selectedAgent.pad.dimensionalState}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-zinc-400">Flux (v)</span>
                      <span className="font-mono">{selectedAgent.pad.nu.toFixed(3)}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-zinc-400">XP</span>
                      <span className="font-bold">{selectedAgent.pad.xp}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-zinc-400">Coherence</span>
                      <span>{(selectedAgent.pad.coherenceScore * 100).toFixed(0)}%</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-zinc-400">Audit Status</span>
                      <span className={`font-bold ${
                        selectedAgent.pad.auditStatus === 'clean' ? 'text-emerald-400' :
                        selectedAgent.pad.auditStatus === 'flagged' ? 'text-yellow-400' : 'text-red-400'
                      }`}>
                        {selectedAgent.pad.auditStatus.toUpperCase()}
                      </span>
                    </div>
                  </div>

                  {/* Pad Contents */}
                  <div className="bg-zinc-700/50 rounded-lg p-3">
                    <h5 className="font-bold text-sm mb-2">Pad Contents</h5>
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div className="bg-zinc-800 rounded p-2">
                        <div className="font-bold">{selectedAgent.pad.notes.length}</div>
                        <div className="text-[10px] text-zinc-500">Notes</div>
                      </div>
                      <div className="bg-zinc-800 rounded p-2">
                        <div className="font-bold">{selectedAgent.pad.sketches.length}</div>
                        <div className="text-[10px] text-zinc-500">Sketches</div>
                      </div>
                      <div className="bg-zinc-800 rounded p-2">
                        <div className="font-bold">{selectedAgent.pad.tools.length}</div>
                        <div className="text-[10px] text-zinc-500">Tools</div>
                      </div>
                    </div>
                  </div>
                </>
              )}

              {/* Capabilities */}
              <div className="bg-zinc-700/50 rounded-lg p-3">
                <h5 className="font-bold text-sm mb-2">Capabilities</h5>
                <div className="flex flex-wrap gap-1">
                  {selectedAgent.capabilities.map(cap => (
                    <span key={cap} className="px-2 py-1 bg-zinc-800 rounded text-xs">
                      {cap}
                    </span>
                  ))}
                </div>
              </div>

              {/* Actions */}
              <div className="space-y-2">
                <button className="w-full py-2 bg-indigo-600 rounded-lg text-xs font-bold uppercase tracking-widest flex items-center justify-center gap-2 hover:bg-indigo-500">
                  <Eye size={14} /> View Polly Pad
                </button>
                <button className="w-full py-2 bg-zinc-700 rounded-lg text-xs font-bold uppercase tracking-widest flex items-center justify-center gap-2 hover:bg-zinc-600">
                  <Settings size={14} /> Configure
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Add Agent Modal */}
      {showAddAgent && (
        <div className="absolute inset-0 bg-black/80 flex items-center justify-center z-50">
          <div className="bg-zinc-800 rounded-2xl p-6 w-96 space-y-4">
            <h3 className="font-black text-lg">Add New Agent</h3>
            <input
              type="text"
              placeholder="Agent name..."
              value={newAgentName}
              onChange={(e) => setNewAgentName(e.target.value)}
              className="w-full bg-zinc-700 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              autoFocus
            />
            <div className="flex gap-2">
              <button
                onClick={() => setShowAddAgent(false)}
                className="flex-1 py-3 bg-zinc-700 rounded-lg text-xs font-bold uppercase tracking-widest hover:bg-zinc-600"
              >
                Cancel
              </button>
              <button
                onClick={handleAddAgent}
                disabled={!newAgentName.trim()}
                className="flex-1 py-3 bg-indigo-600 rounded-lg text-xs font-bold uppercase tracking-widest disabled:opacity-50 hover:bg-indigo-500"
              >
                Add Agent
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
