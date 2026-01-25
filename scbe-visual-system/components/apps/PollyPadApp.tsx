/**
 * Polly Pad App - Personal AI Agent Workspace
 *
 * A "Kindle pad" for AI agents to Draw, Write, save notes,
 * and grow like a little person. Audited by the system like kids at school.
 *
 * @license Apache-2.0
 */
import React, { useState, useCallback } from 'react';
import {
  FileText, Pencil, Wrench, Plus, Trash2, Star,
  TrendingUp, Shield, Activity, Zap, BookOpen
} from 'lucide-react';
import { usePollyPad, TIER_THRESHOLDS, getDimensionalState, GovernanceTier } from '../../lib/scbe-bridge';

interface PollyPadAppProps {
  agentId?: string;
}

const TIER_COLORS: Record<GovernanceTier, string> = {
  'KO': 'bg-pink-500',
  'AV': 'bg-blue-500',
  'RU': 'bg-yellow-500',
  'CA': 'bg-green-500',
  'UM': 'bg-purple-500',
  'DR': 'bg-red-500'
};

const STATE_COLORS: Record<string, string> = {
  'POLLY': 'text-emerald-400',
  'QUASI': 'text-yellow-400',
  'DEMI': 'text-orange-400',
  'COLLAPSED': 'text-red-400'
};

export const PollyPadApp: React.FC<PollyPadAppProps> = ({ agentId = 'visual-computer-local' }) => {
  const { pad, addNote, addSketch, addTool, refresh } = usePollyPad(agentId);
  const [activeTab, setActiveTab] = useState<'notes' | 'sketches' | 'tools' | 'stats'>('notes');
  const [newNoteTitle, setNewNoteTitle] = useState('');
  const [newNoteContent, setNewNoteContent] = useState('');
  const [newToolName, setNewToolName] = useState('');
  const [newToolContent, setNewToolContent] = useState('');

  const handleAddNote = useCallback(() => {
    if (newNoteTitle.trim() && newNoteContent.trim()) {
      addNote(newNoteTitle.trim(), newNoteContent.trim(), ['user-created']);
      setNewNoteTitle('');
      setNewNoteContent('');
    }
  }, [newNoteTitle, newNoteContent, addNote]);

  const handleAddTool = useCallback(() => {
    if (newToolName.trim() && newToolContent.trim()) {
      addTool(newToolName.trim(), 'User-created automation', 'script', newToolContent.trim());
      setNewToolName('');
      setNewToolContent('');
    }
  }, [newToolName, newToolContent, addTool]);

  if (!pad) {
    return (
      <div className="h-full w-full bg-zinc-900 flex items-center justify-center">
        <div className="text-zinc-500 text-sm">Loading Polly Pad...</div>
      </div>
    );
  }

  const xpProgress = pad.xp / (TIER_THRESHOLDS[pad.tier].minXP || 100);
  const tierInfo = TIER_THRESHOLDS[pad.tier];

  return (
    <div className="h-full w-full bg-zinc-900 flex flex-col text-white">
      {/* Header with Agent Info */}
      <div className="p-4 bg-zinc-800 border-b border-zinc-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl ${TIER_COLORS[pad.tier]} flex items-center justify-center`}>
              <BookOpen size={20} />
            </div>
            <div>
              <h2 className="font-black text-lg">{pad.name}</h2>
              <div className="flex items-center gap-2 text-xs text-zinc-400">
                <span className={STATE_COLORS[pad.dimensionalState]}>{pad.dimensionalState}</span>
                <span>|</span>
                <span>{tierInfo.name} (Tier {pad.tier})</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className={`px-3 py-1 rounded-full text-xs font-bold ${
              pad.auditStatus === 'clean' ? 'bg-emerald-500/20 text-emerald-400' :
              pad.auditStatus === 'flagged' ? 'bg-yellow-500/20 text-yellow-400' :
              'bg-red-500/20 text-red-400'
            }`}>
              <Shield size={12} className="inline mr-1" />
              {pad.auditStatus.toUpperCase()}
            </div>
          </div>
        </div>

        {/* XP Progress Bar */}
        <div className="flex items-center gap-3">
          <div className="flex-1 h-2 bg-zinc-700 rounded-full overflow-hidden">
            <div
              className={`h-full ${TIER_COLORS[pad.tier]} transition-all duration-500`}
              style={{ width: `${Math.min(xpProgress * 100, 100)}%` }}
            />
          </div>
          <span className="text-xs text-zinc-400 font-mono">{pad.xp} XP</span>
        </div>

        {/* Dimensional Flux Meter */}
        <div className="mt-3 flex items-center gap-2">
          <Activity size={14} className="text-zinc-500" />
          <span className="text-xs text-zinc-500">Flux (v):</span>
          <div className="flex-1 h-1.5 bg-zinc-700 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                pad.nu >= 0.8 ? 'bg-emerald-400' :
                pad.nu >= 0.5 ? 'bg-yellow-400' :
                pad.nu >= 0.1 ? 'bg-orange-400' : 'bg-red-400'
              }`}
              style={{ width: `${pad.nu * 100}%` }}
            />
          </div>
          <span className="text-xs font-mono text-zinc-400">{pad.nu.toFixed(2)}</span>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-zinc-700">
        {[
          { id: 'notes', icon: FileText, label: 'Notes', count: pad.notes.length },
          { id: 'sketches', icon: Pencil, label: 'Sketches', count: pad.sketches.length },
          { id: 'tools', icon: Wrench, label: 'Tools', count: pad.tools.length },
          { id: 'stats', icon: TrendingUp, label: 'Stats' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`flex-1 px-4 py-3 text-xs font-bold uppercase tracking-widest flex items-center justify-center gap-2 transition-colors ${
              activeTab === tab.id
                ? 'bg-zinc-800 text-white border-b-2 border-sky-500'
                : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            <tab.icon size={14} />
            {tab.label}
            {tab.count !== undefined && (
              <span className="bg-zinc-700 px-1.5 py-0.5 rounded text-[10px]">{tab.count}</span>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'notes' && (
          <div className="space-y-4">
            {/* Add Note Form */}
            <div className="bg-zinc-800 rounded-xl p-4 space-y-3">
              <input
                type="text"
                placeholder="Note title..."
                value={newNoteTitle}
                onChange={(e) => setNewNoteTitle(e.target.value)}
                className="w-full bg-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
              />
              <textarea
                placeholder="Write your note..."
                value={newNoteContent}
                onChange={(e) => setNewNoteContent(e.target.value)}
                className="w-full bg-zinc-700 rounded-lg px-3 py-2 text-sm resize-none h-20 focus:outline-none focus:ring-2 focus:ring-sky-500"
              />
              <button
                onClick={handleAddNote}
                disabled={!newNoteTitle.trim() || !newNoteContent.trim()}
                className="w-full py-2 bg-sky-600 text-white rounded-lg text-xs font-bold uppercase tracking-widest disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                <Plus size={14} /> Add Note (+10 XP)
              </button>
            </div>

            {/* Notes List */}
            {pad.notes.length === 0 ? (
              <div className="text-center text-zinc-500 py-8">
                <FileText size={32} className="mx-auto mb-2 opacity-50" />
                <p className="text-sm">No notes yet. Start writing!</p>
              </div>
            ) : (
              <div className="space-y-2">
                {pad.notes.map(note => (
                  <div key={note.id} className="bg-zinc-800 rounded-xl p-4">
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="font-bold">{note.title}</h3>
                      <span className="text-[10px] text-zinc-500">
                        {new Date(note.createdAt).toLocaleDateString()}
                      </span>
                    </div>
                    <p className="text-sm text-zinc-400 whitespace-pre-wrap">{note.content}</p>
                    {note.tags.length > 0 && (
                      <div className="flex gap-1 mt-2">
                        {note.tags.map(tag => (
                          <span key={tag} className="px-2 py-0.5 bg-zinc-700 rounded text-[10px] text-zinc-400">
                            #{tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'sketches' && (
          <div className="space-y-4">
            <div className="bg-zinc-800 rounded-xl p-4 text-center">
              <Pencil size={32} className="mx-auto mb-2 text-zinc-500" />
              <p className="text-sm text-zinc-400 mb-3">Use the Ink Layer to draw, then save to your pad!</p>
              <p className="text-xs text-zinc-500">Sketches: {pad.sketches.length}</p>
            </div>

            {pad.sketches.map(sketch => (
              <div key={sketch.id} className="bg-zinc-800 rounded-xl p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-bold">{sketch.name}</h3>
                  <span className="text-[10px] text-zinc-500 uppercase">{sketch.sketchType}</span>
                </div>
                <div className="bg-zinc-700 rounded-lg p-2 text-center text-xs text-zinc-500">
                  [Sketch Data]
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'tools' && (
          <div className="space-y-4">
            {/* Add Tool Form */}
            <div className="bg-zinc-800 rounded-xl p-4 space-y-3">
              <input
                type="text"
                placeholder="Tool name..."
                value={newToolName}
                onChange={(e) => setNewToolName(e.target.value)}
                className="w-full bg-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
              />
              <textarea
                placeholder="Tool script/content..."
                value={newToolContent}
                onChange={(e) => setNewToolContent(e.target.value)}
                className="w-full bg-zinc-700 rounded-lg px-3 py-2 text-sm resize-none h-20 font-mono focus:outline-none focus:ring-2 focus:ring-sky-500"
              />
              <button
                onClick={handleAddTool}
                disabled={!newToolName.trim() || !newToolContent.trim()}
                className="w-full py-2 bg-purple-600 text-white rounded-lg text-xs font-bold uppercase tracking-widest disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                <Wrench size={14} /> Add Tool (+25 XP)
              </button>
            </div>

            {/* Tools List */}
            {pad.tools.length === 0 ? (
              <div className="text-center text-zinc-500 py-8">
                <Wrench size={32} className="mx-auto mb-2 opacity-50" />
                <p className="text-sm">No tools yet. Create automations!</p>
              </div>
            ) : (
              <div className="space-y-2">
                {pad.tools.map(tool => (
                  <div key={tool.id} className="bg-zinc-800 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Zap size={14} className={tool.enabled ? 'text-yellow-400' : 'text-zinc-500'} />
                        <h3 className="font-bold">{tool.name}</h3>
                      </div>
                      <span className="text-[10px] text-zinc-500 uppercase">{tool.toolType}</span>
                    </div>
                    <p className="text-sm text-zinc-400">{tool.description}</p>
                    <pre className="mt-2 p-2 bg-zinc-700 rounded text-[10px] font-mono text-zinc-400 overflow-x-auto">
                      {tool.content.substring(0, 100)}{tool.content.length > 100 ? '...' : ''}
                    </pre>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'stats' && (
          <div className="space-y-4">
            {/* Stats Grid */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-zinc-800 rounded-xl p-4 text-center">
                <Star size={24} className="mx-auto mb-2 text-yellow-400" />
                <div className="text-2xl font-black">{pad.xp}</div>
                <div className="text-xs text-zinc-500">Total XP</div>
              </div>
              <div className="bg-zinc-800 rounded-xl p-4 text-center">
                <TrendingUp size={24} className="mx-auto mb-2 text-emerald-400" />
                <div className="text-2xl font-black">Lv.{pad.level}</div>
                <div className="text-xs text-zinc-500">{tierInfo.name}</div>
              </div>
              <div className="bg-zinc-800 rounded-xl p-4 text-center">
                <Activity size={24} className="mx-auto mb-2 text-sky-400" />
                <div className="text-2xl font-black">{(pad.nu * 100).toFixed(0)}%</div>
                <div className="text-xs text-zinc-500">Dimensional Flux</div>
              </div>
              <div className="bg-zinc-800 rounded-xl p-4 text-center">
                <Shield size={24} className="mx-auto mb-2 text-purple-400" />
                <div className="text-2xl font-black">{(pad.coherenceScore * 100).toFixed(0)}%</div>
                <div className="text-xs text-zinc-500">Coherence</div>
              </div>
            </div>

            {/* Tier Progression */}
            <div className="bg-zinc-800 rounded-xl p-4">
              <h3 className="font-bold mb-3 flex items-center gap-2">
                <BookOpen size={16} /> Governance Tier Progression
              </h3>
              <div className="space-y-2">
                {(Object.entries(TIER_THRESHOLDS) as [GovernanceTier, typeof TIER_THRESHOLDS['KO']][]).map(([tier, info]) => {
                  const isActive = tier === pad.tier;
                  const isPast = pad.xp >= info.minXP;
                  return (
                    <div key={tier} className={`flex items-center gap-3 p-2 rounded-lg ${isActive ? 'bg-zinc-700' : ''}`}>
                      <div className={`w-8 h-8 rounded-lg ${isPast ? TIER_COLORS[tier] : 'bg-zinc-700'} flex items-center justify-center text-xs font-bold`}>
                        {tier}
                      </div>
                      <div className="flex-1">
                        <div className="font-bold text-sm">{info.name}</div>
                        <div className="text-[10px] text-zinc-500">{info.minXP}+ XP required</div>
                      </div>
                      {isActive && <span className="text-xs text-sky-400">CURRENT</span>}
                      {isPast && !isActive && <span className="text-xs text-emerald-400">UNLOCKED</span>}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Activity Summary */}
            <div className="bg-zinc-800 rounded-xl p-4">
              <h3 className="font-bold mb-3">Activity Summary</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-zinc-400">Notes Created</span>
                  <span>{pad.notes.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Sketches Saved</span>
                  <span>{pad.sketches.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Tools Built</span>
                  <span>{pad.tools.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Audit Status</span>
                  <span className={
                    pad.auditStatus === 'clean' ? 'text-emerald-400' :
                    pad.auditStatus === 'flagged' ? 'text-yellow-400' : 'text-red-400'
                  }>{pad.auditStatus}</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
