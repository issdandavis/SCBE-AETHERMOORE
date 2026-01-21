/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import React, { useState, useEffect } from 'react';
import { Play, Save, RotateCcw, Layout, Code as CodeIcon, Terminal } from 'lucide-react';

const INITIAL_CODE = `// Kindle OS - Web Development Sandbox
// Type your code here to see it live!

const App = () => {
  return (
    <div style={{ 
      padding: '2rem', 
      textAlign: 'center',
      fontFamily: 'sans-serif'
    }}>
      <h1 style={{ color: '#3b82f6' }}>Hello Kindle!</h1>
      <p>This is a live preview generated in the sandboxed IDE.</p>
    </div>
  );
};

export default App;`;

export const CodeEditorApp: React.FC = () => {
    const [code, setCode] = useState(INITIAL_CODE);
    const [view, setView] = useState<'editor' | 'preview'>('editor');
    const [logs, setLogs] = useState<string[]>(['IDE Initialized...', 'E-ink syntax highighting active.']);

    const runCode = () => {
        setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] Running build process...`, 'Build successful!']);
        setView('preview');
    };

    return (
        <div className="h-full w-full bg-[#1e1e1e] flex flex-col text-zinc-300">
            {/* Toolbar */}
            <div className="px-4 py-2 bg-[#252526] border-b border-zinc-800 flex justify-between items-center">
                <div className="flex gap-2">
                    <button onClick={() => setView('editor')} className={`px-4 py-1.5 rounded-lg text-xs font-black uppercase tracking-widest flex items-center gap-2 ${view === 'editor' ? 'bg-zinc-700 text-white' : 'hover:bg-zinc-800 text-zinc-500'}`}>
                        <CodeIcon size={14} /> Editor
                    </button>
                    <button onClick={() => setView('preview')} className={`px-4 py-1.5 rounded-lg text-xs font-black uppercase tracking-widest flex items-center gap-2 ${view === 'preview' ? 'bg-zinc-700 text-white' : 'hover:bg-zinc-800 text-zinc-500'}`}>
                        <Layout size={14} /> Preview
                    </button>
                </div>
                <div className="flex gap-2">
                    <button onClick={runCode} className="px-4 py-1.5 bg-emerald-600 text-white rounded-lg text-[10px] font-black uppercase tracking-widest flex items-center gap-2 hover:bg-emerald-500">
                        <Play size={14} fill="currentColor" /> Run
                    </button>
                    <button className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-500"><Save size={16} /></button>
                </div>
            </div>

            <div className="flex-1 flex overflow-hidden">
                {view === 'editor' ? (
                    <div className="flex-1 flex flex-col overflow-hidden">
                        <textarea 
                            value={code}
                            onChange={(e) => setCode(e.target.value)}
                            className="flex-1 bg-transparent p-6 font-mono text-sm resize-none focus:outline-none scrollbar-thin scrollbar-thumb-zinc-700"
                            spellCheck={false}
                        />
                        {/* Terminal HUD */}
                        <div className="h-32 bg-black/40 border-t border-zinc-800 p-4 font-mono text-[10px] overflow-y-auto">
                            <div className="flex items-center gap-2 text-zinc-500 mb-2 uppercase tracking-widest font-black">
                                <Terminal size={12} /> Output
                            </div>
                            {logs.map((log, i) => (
                                <div key={i} className="text-zinc-400 mb-1 leading-tight">{log}</div>
                            ))}
                        </div>
                    </div>
                ) : (
                    <div className="flex-1 bg-white p-8 flex items-center justify-center">
                         <div className="max-w-md w-full border border-zinc-200 rounded-2xl p-12 text-center text-zinc-800 shadow-sm">
                             <h1 className="text-3xl font-black text-sky-600 mb-4">Hello Kindle!</h1>
                             <p className="text-zinc-500 leading-relaxed">This is a live preview generated in the sandboxed IDE.</p>
                             <div className="mt-8 pt-8 border-t border-zinc-100 flex justify-center gap-4 text-[10px] font-black uppercase tracking-[0.2em] text-zinc-400">
                                 <span>Build v1.0.0</span>
                                 <span>•</span>
                                 <span>React 19 Runtime</span>
                             </div>
                         </div>
                    </div>
                )}
            </div>
        </div>
    );
};