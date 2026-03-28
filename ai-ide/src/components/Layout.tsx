
import React, { useState } from 'react';
import { Menu, X, Settings, Play, Eye, Code, Zap, PanelLeftClose, PanelLeftOpen, MessageSquare, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Resizable } from 're-resizable';

interface LayoutProps {
  children: React.ReactNode;
  sidebar: React.ReactNode;
  terminal: React.ReactNode;
  aiPanel: React.ReactNode;
  onModeChange: (mode: 'show-me' | 'do-it') => void;
  currentMode: 'show-me' | 'do-it';
  onSettingsClick?: () => void;
  onRunClick?: () => void;
  isAiOpen: boolean;
  onToggleAi: () => void;
}

export const Layout: React.FC<LayoutProps> = ({ 
  children, 
  sidebar, 
  terminal,
  aiPanel,
  onModeChange,
  currentMode,
  onSettingsClick,
  onRunClick,
  isAiOpen,
  onToggleAi
}) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <div className="flex h-screen w-full bg-slate-950 text-slate-200 overflow-hidden font-sans">
      {/* Mobile Header */}
      <div className="md:hidden fixed top-0 w-full bg-slate-900 border-b border-slate-800 z-50 flex items-center justify-between p-4">
        <div className="flex items-center gap-2">
          <Zap className="text-blue-500 w-5 h-5" />
          <span className="font-bold text-lg">SCBE-AETHERMOORE</span>
        </div>
        <div className="flex items-center gap-2">
            <button 
                onClick={onToggleAi}
                className={`p-2 rounded-md transition-colors ${isAiOpen ? 'bg-blue-600/20 text-blue-400' : 'hover:bg-slate-800 text-slate-400'}`}
            >
                <Sparkles className="w-5 h-5" />
            </button>
            <button onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)} className="p-1 hover:bg-slate-800 rounded">
            {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
        </div>
      </div>

      {/* Sidebar */}
      <AnimatePresence mode="wait">
        {(isSidebarOpen || isMobileMenuOpen) && (
          <motion.aside
            initial={{ x: -300, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -300, opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className={`
              fixed md:relative z-40 w-64 h-full bg-slate-900 border-r border-slate-800 flex flex-col
              ${isMobileMenuOpen ? 'top-14 block shadow-2xl' : 'hidden md:flex'}
            `}
          >
            {/* Sidebar Header */}
            <div className="p-4 border-b border-slate-800 flex items-center justify-between h-14">
              <div className="flex items-center gap-2 font-semibold select-none">
                <Code className="w-5 h-5 text-blue-400" />
                <span>Explorer</span>
              </div>
              <button 
                onClick={() => {
                  setIsSidebarOpen(false);
                  setIsMobileMenuOpen(false);
                }}
                className="p-1.5 hover:bg-slate-800 rounded-md text-slate-400 hover:text-white transition-colors"
                title="Collapse Sidebar"
              >
                <PanelLeftClose className="w-4 h-4" />
              </button>
            </div>
            
            {/* File Tree */}
            <div className="flex-1 overflow-y-auto custom-scrollbar">
              {sidebar}
            </div>

            {/* Bottom Sidebar Actions */}
            <div className="p-4 border-t border-slate-800 bg-slate-900/50">
               <div className="flex items-center gap-2 text-xs text-slate-500 mb-3 uppercase font-bold tracking-wider select-none">
                  AI Modes
               </div>
               <div className="grid grid-cols-2 gap-2 mb-4">
                 <button
                   onClick={() => onModeChange('show-me')}
                   className={`flex items-center justify-center gap-2 p-2 rounded-md text-sm font-medium transition-all duration-200 border ${currentMode === 'show-me' ? 'bg-blue-600/10 border-blue-500/50 text-blue-400 shadow-[0_0_10px_rgba(59,130,246,0.2)]' : 'bg-slate-800 border-transparent text-slate-400 hover:bg-slate-700 hover:text-slate-200'}`}
                 >
                   <Eye className="w-4 h-4" />
                   Show Me
                 </button>
                 <button
                   onClick={() => onModeChange('do-it')}
                   className={`flex items-center justify-center gap-2 p-2 rounded-md text-sm font-medium transition-all duration-200 border ${currentMode === 'do-it' ? 'bg-emerald-600/10 border-emerald-500/50 text-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.2)]' : 'bg-slate-800 border-transparent text-slate-400 hover:bg-slate-700 hover:text-slate-200'}`}
                 >
                   <Play className="w-4 h-4" />
                   Do It
                 </button>
               </div>

               <button 
                onClick={onSettingsClick}
                className="flex items-center gap-2 w-full p-2 rounded-md text-sm text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors"
               >
                 <Settings className="w-4 h-4" />
                 <span>Settings</span>
               </button>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 h-full pt-14 md:pt-0 relative bg-[#1e1e1e]">
         {/* Top Toolbar (Desktop) */}
         <div className="hidden md:flex items-center justify-between h-14 px-4 border-b border-slate-800 bg-slate-900">
            <div className="flex items-center gap-2">
              {!isSidebarOpen && (
                <button 
                  onClick={() => setIsSidebarOpen(true)}
                  className="p-1.5 hover:bg-slate-800 rounded-md text-slate-400 hover:text-white transition-colors"
                  title="Expand Sidebar"
                >
                  <PanelLeftOpen className="w-4 h-4" />
                </button>
              )}
            </div>

            <div className="flex items-center gap-3">
                {/* AI Toggle Button */}
                <button
                    onClick={onToggleAi}
                    className={`
                        flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors border
                        ${isAiOpen 
                            ? 'bg-blue-600/10 border-blue-500/50 text-blue-400' 
                            : 'bg-slate-800 border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-700'}
                    `}
                    title="Toggle AI Assistant"
                >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>AI Assistant</span>
                </button>

                {/* Run Button in Header */}
                <button
                onClick={onRunClick}
                className="flex items-center gap-2 px-3 py-1.5 bg-green-700 hover:bg-green-600 text-white rounded-md text-sm font-medium transition-colors shadow-sm"
                title="Run Active File"
                >
                <Play className="w-3.5 h-3.5 fill-current" />
                Run
                </button>
            </div>
         </div>

         <div className="flex flex-1 overflow-hidden">
            {/* Editor Area (Flex Grow) */}
            <div className="flex-1 flex flex-col min-w-0">
                <div className="flex-1 overflow-hidden relative">
                    {children}
                </div>

                {/* Resizable Terminal Area */}
                <Resizable
                    defaultSize={{ width: '100%', height: '33%' }}
                    minHeight="40px"
                    maxHeight="80vh"
                    enable={{ top: true, right: false, bottom: false, left: false, topRight: false, bottomRight: false, bottomLeft: false, topLeft: false }}
                    handleClasses={{ top: 'h-1 bg-slate-800 hover:bg-blue-500/50 cursor-row-resize transition-colors z-10' }}
                    className="flex flex-col bg-slate-900 shadow-[0_-1px_10px_rgba(0,0,0,0.3)] z-30"
                >
                    {terminal}
                </Resizable>
            </div>

            {/* AI Panel (Right Side) */}
            {aiPanel}
         </div>
      </main>
    </div>
  );
};
