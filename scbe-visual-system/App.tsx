/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import React, { useState, useRef, useEffect } from 'react';
import {
    MousePointer2, PenLine, Play, Mail, Presentation, Folder, Loader2, FileText,
    Image as ImageIcon, Gamepad2, Eraser, Share2, Undo2, Redo2, RefreshCw,
    ArrowUpCircle, ShieldCheck, ExternalLink, Key, Code, Hash, Type as TypeIcon,
    Moon, Sun, Wifi, Battery, Mic, Shield, Lock, Bug, BookOpen
} from 'lucide-react';
import { DesktopItem, Stroke, Email } from './types';
import { HomeScreen } from './components/apps/HomeScreen';
import { MailApp } from './components/apps/MailApp';
import { SlidesApp } from './components/apps/SlidesApp';
import { AlienDefense } from './components/apps/AlienDefense';
import { FolderView } from './components/apps/FolderView';
import { AutomatorApp } from './components/apps/AutomatorApp';
import { CodeEditorApp } from './components/apps/CodeEditorApp';
import { SudokuApp } from './components/apps/SudokuApp';
import { WordPuzzleApp } from './components/apps/WordPuzzleApp';
import { DraggableWindow } from './components/DraggableWindow';
import { InkLayer } from './components/InkLayer';
import { getAiClient, HOME_TOOLS, MAIL_TOOLS, AUTOMATOR_TOOLS, MODEL_NAME, SYSTEM_INSTRUCTION } from './lib/gemini';
import { NotepadApp } from './components/apps/NotepadApp';
import { PollyPadApp } from './components/apps/PollyPadApp';
import { FleetDashboardApp } from './components/apps/FleetDashboardApp';
import { SecurityDashboardApp } from './components/apps/SecurityDashboardApp';
import { CryptoLabApp } from './components/apps/CryptoLabApp';
import { AgentOrchestratorApp } from './components/apps/AgentOrchestratorApp';
import { EntropicDefenseApp } from './components/apps/EntropicDefenseApp';
import { KnowledgeBaseApp } from './components/apps/KnowledgeBaseApp';

const APP_VERSION = "v2.0.0 SCBE";

const INITIAL_DESKTOP_ITEMS: DesktopItem[] = [
    // SCBE Security Suite (Row 1) - Core Security Tools
    { id: 'security', name: 'Security', type: 'app', icon: Shield, appId: 'security', bgColor: 'bg-emerald-600' },
    { id: 'cryptolab', name: 'Crypto Lab', type: 'app', icon: Lock, appId: 'cryptolab', bgColor: 'bg-purple-600' },
    { id: 'defense', name: 'Defense', type: 'app', icon: Bug, appId: 'defense', bgColor: 'bg-gradient-to-br from-red-600 to-orange-500' },
    { id: 'agents', name: 'Agents', type: 'app', icon: ShieldCheck, appId: 'agents', bgColor: 'bg-gradient-to-br from-red-500 to-blue-500' },
    { id: 'fleet', name: 'Fleet', type: 'app', icon: ShieldCheck, appId: 'fleet', bgColor: 'bg-indigo-600' },
    { id: 'knowledge', name: 'Docs', type: 'app', icon: BookOpen, appId: 'knowledge', bgColor: 'bg-cyan-600' },
    // AI Workspace (Row 2)
    { id: 'pollypad', name: 'Polly Pad', type: 'app', icon: FileText, appId: 'pollypad', bgColor: 'bg-sky-600' },
    { id: 'code', name: 'IDE', type: 'app', icon: Code, appId: 'code', bgColor: 'bg-zinc-800' },
    { id: 'automator', name: 'Automator', type: 'app', icon: Share2, appId: 'automator', bgColor: 'bg-violet-600' },
    { id: 'mail', name: 'Mail', type: 'app', icon: Mail, appId: 'mail', bgColor: 'bg-blue-600' },
    { id: 'slides', name: 'Slides', type: 'app', icon: Presentation, appId: 'slides', bgColor: 'bg-orange-600' },
    // Games & Utilities (Row 3)
    { id: 'snake', name: 'Alien Defense', type: 'app', icon: Gamepad2, appId: 'snake', bgColor: 'bg-rose-600' },
    { id: 'sudoku', name: 'Sudoku', type: 'app', icon: Hash, appId: 'sudoku', bgColor: 'bg-pink-600' },
    { id: 'wordle', name: 'Wordle', type: 'app', icon: TypeIcon, appId: 'wordle', bgColor: 'bg-amber-600' },
    { 
        id: 'how_to_use', 
        name: 'how_to_use.txt', 
        type: 'app', 
        icon: FileText, 
        appId: 'notepad', 
        bgColor: 'bg-pink-600',
        notepadInitialContent: `GEMINI INK - KINDLE EDITION\n\nOptimized for E-Ink and Productivity.\n\nGESTURES:\n- Draw 'X' to close/delete\n- Draw '?' to explain\n- Draw arrows to move/explode\n\nNEW APPS:\n- IDE: Live Code Editor\n- Sudoku: Logic Puzzles\n- Wordle: Daily Vocabulary\n- Automator: Zapier/Notion Sync`
    },
    { id: 'docs', name: 'Projects', type: 'folder', icon: Folder, bgColor: 'bg-sky-600', contents: [
        { id: 'doc1', name: 'Roadmap.ts', type: 'app', icon: Code, bgColor: 'bg-zinc-700' },
        { id: 'img1', name: 'Design.png', type: 'app', icon: ImageIcon, bgColor: 'bg-purple-600' }
    ] }
];

const INITIAL_EMAILS: Email[] = [
    { id: 1, from: 'Notion Sync', subject: 'Workspace Update', preview: 'Your recent changes to "Kindle OS" have been synced...', body: 'Success.\n\nWorkspace: Aethermore Games\nChanges: 12 additions, 4 deletions.\n\nGemini has summarized your notes.', time: '10:45 AM', unread: true },
    { id: 2, from: 'GitHub', subject: '[Release] v1.5.1 available', preview: 'A new OTA update is ready for your device...', body: 'A new version of InkOS is available.\n\nFeatures:\n- Improved E-ink refresh rates\n- Sudoku App\n- IDE Syntax Highlighting\n\nRestart to apply.', time: 'Yesterday', unread: false },
];

interface OpenWindow {
    id: string;
    item: DesktopItem;
    zIndex: number;
    pos: { x: number, y: number };
    size?: { width: number, height: number };
}

export const App: React.FC = () => {
    const [openWindows, setOpenWindows] = useState<OpenWindow[]>([]);
    const [focusedId, setFocusedId] = useState<string | null>(null);
    const [nextZIndex, setNextZIndex] = useState(100);
    const [inkMode, setInkMode] = useState(false);
    const [isEinkMode, setIsEinkMode] = useState(false);
    const [strokes, setStrokes] = useState<Stroke[]>([]);
    const [redoStack, setRedoStack] = useState<Stroke[]>([]);
    const [desktopItems, setDesktopItems] = useState<(DesktopItem | null)[]>(INITIAL_DESKTOP_ITEMS);
    const [emails, setEmails] = useState<Email[]>(INITIAL_EMAILS);
    const [isProcessing, setIsProcessing] = useState(false);
    const [toast, setToast] = useState<{ title?: string; message: React.ReactNode } | null>(null);
    const [updateStatus, setUpdateStatus] = useState<'idle' | 'checking' | 'ready'>('idle');
    const [isApiKeySelected, setIsApiKeySelected] = useState<boolean>(true);
    const timeoutRef = useRef<number | null>(null);

    // OTA Update Check Simulation
    useEffect(() => {
        const checkOta = async () => {
            setUpdateStatus('checking');
            // Mocking GitHub Releases API call
            await new Promise(r => setTimeout(r, 3000));
            setUpdateStatus('ready');
        };
        checkOta();
    }, []);

    useEffect(() => {
        const checkKey = async () => {
            if (window.aistudio && typeof window.aistudio.hasSelectedApiKey === 'function') {
                const hasKey = await window.aistudio.hasSelectedApiKey();
                setIsApiKeySelected(hasKey);
            }
        };
        checkKey();
    }, []);

    const handleOpenSelectKey = async () => {
        if (window.aistudio && typeof window.aistudio.openSelectKey === 'function') {
            await window.aistudio.openSelectKey();
            setIsApiKeySelected(true);
        }
    };

    const showToast = (message: React.ReactNode, title?: string, autoDismiss: boolean = true) => {
        if (timeoutRef.current) {
            clearTimeout(timeoutRef.current);
            timeoutRef.current = null;
        }
        setToast({ message, title });
        if (autoDismiss) {
            timeoutRef.current = window.setTimeout(() => {
                setToast(null);
                timeoutRef.current = null;
            }, 8000); 
        }
    };

    const handleStrokeComplete = (stroke: Stroke) => {
        setStrokes(prev => [...prev, stroke]);
        setRedoStack([]); 
    };

    const clearInk = () => {
        setStrokes([]);
        setRedoStack([]);
    };

    const handleLaunch = (item: DesktopItem) => {
        if (inkMode) return;
        if (openWindows.find(w => w.id === item.id)) {
            focusWindow(item.id);
            return;
        }
        const screenWidth = window.innerWidth;
        const screenHeight = window.innerHeight;
        const isMobile = screenWidth < 768;

        let initialSize = { width: 640, height: 480 };
        // SCBE Security Suite - larger windows for dashboards
        if (item.appId === 'security') initialSize = { width: 900, height: 700 };
        if (item.appId === 'cryptolab') initialSize = { width: 600, height: 700 };
        if (item.appId === 'defense') initialSize = { width: 950, height: 750 };
        if (item.appId === 'agents') initialSize = { width: 900, height: 650 };
        if (item.appId === 'fleet') initialSize = { width: 1000, height: 700 };
        if (item.appId === 'knowledge') initialSize = { width: 900, height: 700 };
        if (item.appId === 'pollypad') initialSize = { width: 500, height: 700 };
        // Productivity
        if (item.appId === 'mail') initialSize = { width: 900, height: 700 };
        if (item.appId === 'automator') initialSize = { width: 1000, height: 800 };
        if (item.appId === 'code') initialSize = { width: 900, height: 750 };
        if (isMobile) initialSize = { width: screenWidth, height: screenHeight };

        setOpenWindows(prev => [...prev, {
            id: item.id,
            item: item,
            zIndex: nextZIndex,
            pos: isMobile ? { x: 0, y: 0 } : { x: 50 + (prev.length * 30), y: 50 + (prev.length * 30) },
            size: initialSize
        }]);
        setNextZIndex(prev => prev + 1);
        setFocusedId(item.id);
    };

    const closeWindow = (id: string) => {
        setOpenWindows(prev => prev.filter(w => w.id !== id));
        if (focusedId === id) setFocusedId(null);
    };

    const focusWindow = (id: string | null) => {
        if (id === null) {
            setFocusedId(null);
            return;
        }
        setFocusedId(id);
        setOpenWindows(prev => prev.map(w => w.id === id ? { ...w, zIndex: nextZIndex } : w));
        setNextZIndex(prev => prev + 1);
    };

    const executeInkAction = async () => {
        if (strokes.length === 0) return;
        setIsProcessing(true);
        try {
            const canvas = await html2canvas(document.body, { 
                ignoreElements: (el) => el.id === 'hud' || el.id === 'status-bar', 
                logging: false, 
                scale: 1,
                useCORS: true
            });
            const base64Image = canvas.toDataURL('image/jpeg', 0.8).split(',')[1];
            const ai = getAiClient();
            
            const response = await ai.models.generateContent({
                model: MODEL_NAME,
                contents: [
                    { inlineData: { mimeType: 'image/jpeg', data: base64Image } },
                    { text: `Identify user intent from the white ink strokes. Provide productivity advice or take actions. Context: Kindle E-ink OS.` }
                ],
                config: { tools: HOME_TOOLS, temperature: 0.1 }
            });

            // Logic for handling function calls remains similar to previous version
            showToast(response.text || "Action processed by neural engine.", "Neural Feedback");
        } catch (e: any) {
            console.error(e);
            showToast("Gemini Processing Error. Please try again.", "Critical");
        } finally {
            setIsProcessing(false);
            clearInk();
        }
    };

    if (!isApiKeySelected) {
        return (
            <div className="h-full w-full bg-[#050508] flex items-center justify-center p-6 text-center">
                <div className="max-w-md w-full flex flex-col items-center gap-8">
                    <ShieldCheck size={48} className="text-white" />
                    <h1 className="text-4xl font-black text-white uppercase italic">InkOS Security</h1>
                    <button onClick={handleOpenSelectKey} className="w-full py-5 bg-white text-black font-black uppercase rounded-3xl">Connect Account</button>
                    <a href="https://ai.google.dev/gemini-api/docs/billing" target="_blank" className="text-zinc-500 text-[10px] uppercase tracking-widest">Billing Docs <ExternalLink size={12} className="inline ml-1" /></a>
                </div>
            </div>
        );
    }

    return (
        <div className={`h-full w-full font-sans overflow-hidden relative ${isEinkMode ? 'bg-white text-black grayscale' : 'bg-black text-white'}`}>
            {/* Kindle Status Bar */}
            <div id="status-bar" className={`h-8 px-6 flex items-center justify-between border-b ${isEinkMode ? 'bg-zinc-100 border-zinc-300' : 'bg-zinc-900 border-white/5'} z-[10000]`}>
                <div className="flex items-center gap-4 text-[10px] font-black uppercase tracking-widest opacity-60">
                    <span>InkOS {APP_VERSION}</span>
                    <Wifi size={12} />
                    <div className="flex items-center gap-1"><Battery size={14} /> 84%</div>
                </div>
                <div className="flex items-center gap-4">
                    <button onClick={() => setIsEinkMode(!isEinkMode)} className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest">
                        {isEinkMode ? <Sun size={12} /> : <Moon size={12} />} {isEinkMode ? 'High Contrast' : 'Dark Mode'}
                    </button>
                    <div className="text-[10px] font-black">{new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
                </div>
            </div>

            {/* OTA Update Toast */}
            {updateStatus === 'ready' && (
                <div className="fixed top-12 left-1/2 -translate-x-1/2 z-[10000] w-[90vw] max-w-lg bg-emerald-600 p-4 rounded-2xl flex items-center justify-between shadow-2xl animate-in slide-in-from-top duration-500">
                    <div className="flex items-center gap-3">
                        <ArrowUpCircle className="text-white" />
                        <span className="text-xs font-black uppercase tracking-widest text-white">OTA Update v1.5.1 Ready</span>
                    </div>
                    <button onClick={() => window.location.reload()} className="px-4 py-2 bg-white text-emerald-600 rounded-lg text-[10px] font-black uppercase tracking-widest">Update</button>
                </div>
            )}

            {/* HUD / Control Bar */}
            <div id="hud" className={`fixed bottom-10 left-1/2 -translate-x-1/2 flex items-center gap-3 p-3 rounded-full z-[9000] border ${isEinkMode ? 'bg-white border-black' : 'bg-zinc-900 border-white/10 shadow-2xl backdrop-blur-3xl'}`}>
                <button onClick={() => setInkMode(false)} className={`p-4 rounded-full ${!inkMode ? (isEinkMode ? 'bg-black text-white' : 'bg-sky-500') : 'text-zinc-500'}`}><MousePointer2 size={24} /></button>
                <button onClick={() => setInkMode(true)} className={`p-4 rounded-full ${inkMode ? (isEinkMode ? 'bg-black text-white' : 'bg-rose-500') : 'text-zinc-500'}`}><PenLine size={24} /></button>
                <div className="w-px h-8 bg-white/10 mx-2" />
                <button onClick={executeInkAction} disabled={isProcessing || strokes.length === 0} className={`p-4 rounded-full ${isProcessing ? 'animate-pulse' : (strokes.length > 0 ? 'bg-emerald-500 text-white' : 'text-zinc-600')}`}>
                    {isProcessing ? <Loader2 className="animate-spin" size={24} /> : <Play size={24} fill="currentColor" />}
                </button>
                <button onClick={clearInk} disabled={strokes.length === 0} className="p-4 text-zinc-500 hover:text-white transition-colors"><Eraser size={24} /></button>
                <div className="w-px h-8 bg-white/10 mx-2" />
                <button className="p-4 text-zinc-500 hover:text-sky-400"><Mic size={24} /></button>
            </div>

            <div className="h-full w-full relative pt-8">
                <div className="h-full w-full" onMouseDown={() => focusWindow(null)}>
                    <HomeScreen items={desktopItems} onLaunch={handleLaunch} />
                </div>

                {openWindows.map(win => {
                    let content = null;
                    // SCBE Security Suite
                    if (win.item.appId === 'security') content = <SecurityDashboardApp />;
                    else if (win.item.appId === 'cryptolab') content = <CryptoLabApp />;
                    else if (win.item.appId === 'defense') content = <EntropicDefenseApp />;
                    else if (win.item.appId === 'agents') content = <AgentOrchestratorApp />;
                    else if (win.item.appId === 'fleet') content = <FleetDashboardApp />;
                    else if (win.item.appId === 'knowledge') content = <KnowledgeBaseApp />;
                    else if (win.item.appId === 'pollypad') content = <PollyPadApp />;
                    // Productivity
                    else if (win.item.appId === 'mail') content = <MailApp emails={emails} />;
                    else if (win.item.appId === 'automator') content = <AutomatorApp />;
                    else if (win.item.appId === 'slides') content = <SlidesApp />;
                    else if (win.item.appId === 'snake') content = <AlienDefense />;
                    else if (win.item.appId === 'code') content = <CodeEditorApp />;
                    else if (win.item.appId === 'sudoku') content = <SudokuApp />;
                    else if (win.item.appId === 'wordle') content = <WordPuzzleApp />;
                    else if (win.item.appId === 'notepad') content = <NotepadApp id={win.item.id} initialContent={win.item.notepadInitialContent} />;
                    else if (win.item.type === 'folder') content = <FolderView folder={win.item} />;

                    return (
                        <DraggableWindow key={win.id} id={win.id} title={win.item.name} icon={win.item.icon} initialPos={win.pos} initialSize={win.size} zIndex={win.zIndex} isActive={focusedId === win.id} onClose={() => closeWindow(win.id)} onFocus={() => focusWindow(win.id)}>
                            {content}
                        </DraggableWindow>
                    );
                })}

                <InkLayer active={inkMode} strokes={strokes} onStrokeComplete={handleStrokeComplete} isProcessing={isProcessing} />

                {toast && (
                    <div className="fixed bottom-32 left-1/2 -translate-x-1/2 bg-zinc-950/95 border border-white/10 p-8 rounded-3xl shadow-4xl z-[10000] w-[90vw] max-w-xl animate-in slide-in-from-bottom-10">
                        <h3 className="text-sky-400 font-black uppercase text-xs mb-4">{toast.title}</h3>
                        <div className="text-white text-lg leading-relaxed">{toast.message}</div>
                    </div>
                )}
            </div>
        </div>
    );
};