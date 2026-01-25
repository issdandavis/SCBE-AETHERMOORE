
/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import React, { useState, useEffect } from 'react';
import { Settings, Zap, Database, MessageSquare, Github, Share2, BookOpen, Terminal, Activity, CheckCircle, Clock } from 'lucide-react';

// FIX: Define FileText before it is used in the NODES array
const FileText = ({ size, className }: { size: number, className: string }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/>
        <line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/>
    </svg>
);

const NODES = [
    { id: 'jira', name: 'Jira Cloud', icon: Settings, color: 'text-blue-500', bg: 'bg-blue-500/10', pos: { x: 20, y: 25 }, subtitle: 'Aethermore (KAN)', status: 'online' },
    { id: 'notion', name: 'Notion', icon: FileText, color: 'text-zinc-100', bg: 'bg-zinc-500/10', pos: { x: 50, y: 20 }, subtitle: 'Kindle Docs', status: 'online' },
    { id: 'zapier', name: 'Zapier', icon: Zap, color: 'text-orange-500', bg: 'bg-orange-500/10', pos: { x: 50, y: 50 }, subtitle: 'Workflow Hub', status: 'online' },
    { id: 'kindle', name: 'Kindle Vellum', icon: BookOpen, color: 'text-amber-500', bg: 'bg-amber-500/10', pos: { x: 80, y: 25 }, subtitle: 'KDP Publishing', status: 'idle' },
    { id: 'slack', name: 'Slack', icon: MessageSquare, color: 'text-purple-500', bg: 'bg-purple-500/10', pos: { x: 80, y: 75 }, subtitle: 'Team Comms', status: 'online' },
    { id: 'github', name: 'GitHub', icon: Github, color: 'text-zinc-400', bg: 'bg-zinc-400/10', pos: { x: 20, y: 75 }, subtitle: 'InkOS Repos', status: 'deploying' },
    { id: 'database', name: 'Cloud Sync', icon: Database, color: 'text-emerald-500', bg: 'bg-emerald-500/10', pos: { x: 50, y: 85 }, subtitle: 'Global Data', status: 'online' },
];

export const AutomatorApp: React.FC = () => {
    const [logs, setLogs] = useState<string[]>([
        "SYSTEM: Initialization complete.",
        "NOTION: Synced 12 active blocks.",
        "ZAPIER: Webhook active on /prod/sync.",
        "GITHUB: Deployment v1.5.0 finalized."
    ]);

    useEffect(() => {
        const interval = setInterval(() => {
            const events = [
                "JIRA: Issue KAN-402 updated.",
                "ZAPIER: Workflow triggered.",
                "NOTION: Auto-save complete.",
                "SYSTEM: Checksum verified.",
                "GITHUB: Pushing production tag..."
            ];
            setLogs(prev => [...prev.slice(-5), `[${new Date().toLocaleTimeString()}] ${events[Math.floor(Math.random() * events.length)]}`]);
        }, 6000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="h-full w-full bg-[#05050a] flex flex-col overflow-hidden relative">
            <div className="p-6 border-b border-zinc-800/50 bg-zinc-900/40 flex justify-between items-center z-20 backdrop-blur-xl shrink-0">
                <div className="flex items-center gap-3">
                    <Share2 className="text-sky-400" size={20} />
                    <div>
                        <h2 className="font-black text-sm tracking-widest text-zinc-100 uppercase italic">Automation Hub Pro</h2>
                        <p className="text-[10px] text-zinc-500 font-mono tracking-tighter">OTA STATUS: SYNCED</p>
                    </div>
                </div>
                <div className="flex items-center gap-6">
                    <div className="px-4 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center gap-2">
                        <Activity className="text-emerald-500 animate-pulse" size={12} />
                        <span className="text-emerald-500 text-[10px] font-black uppercase tracking-widest">7 Services Active</span>
                    </div>
                </div>
            </div>

            <div className="flex-1 relative bg-[radial-gradient(#1c1c21_1.5px,transparent_1.5px)] [background-size:40px_40px]">
                <div className="absolute inset-0 overflow-auto p-20 min-w-[900px]">
                    {NODES.map(node => (
                        <div key={node.id} style={{ left: `${node.pos.x}%`, top: `${node.pos.y}%` }} className="absolute -translate-x-1/2 -translate-y-1/2 group">
                            <div className={`w-40 h-40 rounded-[2.5rem] ${node.bg} border border-white/5 flex flex-col items-center justify-center gap-3 hover:border-sky-500/40 transition-all duration-700 cursor-pointer backdrop-blur-2xl shadow-3xl`}>
                                {/* FIX: Added size prop to the icon component */}
                                <node.icon size={48} className={`${node.color} w-12 h-12 mb-1 group-hover:scale-110 transition-transform`} />
                                <div className="text-center">
                                    <span className="text-xs font-black text-white block uppercase">{node.name}</span>
                                    <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-tighter">{node.subtitle}</span>
                                </div>
                                <div className="mt-2 flex items-center gap-1.5">
                                    {node.status === 'online' ? <CheckCircle size={10} className="text-emerald-500" /> : <Clock size={10} className="text-amber-500" />}
                                    <span className={`text-[8px] font-black uppercase tracking-widest ${node.status === 'online' ? 'text-emerald-500' : 'text-amber-500'}`}>{node.status}</span>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>

                <div className="absolute bottom-8 left-8 p-6 bg-zinc-950/90 border border-white/5 rounded-3xl backdrop-blur-3xl w-80 shadow-4xl">
                    <div className="flex items-center gap-3 mb-4 border-b border-white/5 pb-3 font-black text-[10px] text-zinc-400 uppercase tracking-widest">
                        <Terminal size={14} /> Global Hub Log
                    </div>
                    <div className="space-y-2 h-32 overflow-hidden">
                        {logs.map((log, i) => (
                            <p key={i} className="text-[9px] font-mono text-zinc-500 truncate"><span className="text-sky-500/60 italic mr-1">{">>>"}</span> {log}</p>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};
