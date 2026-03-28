
import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, X, Sparkles, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API_BASE = 'http://localhost:8100/api';

interface Message {
  id: string;
  role: 'user' | 'ai';
  content: string;
  timestamp: number;
}

interface AIAssistantProps {
  isOpen: boolean;
  onClose: () => void;
  activeFileName?: string;
  activeFileContent?: string;
  mode: 'show-me' | 'do-it';
}

export const AIAssistant: React.FC<AIAssistantProps> = ({ 
  isOpen, 
  onClose, 
  activeFileName, 
  activeFileContent,
  mode 
}) => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'init',
      role: 'ai',
      content: 'Hello! I am your AI Architect. I can help you write code, explain concepts, or debug issues. What are we building today?',
      timestamp: Date.now()
    }
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: Date.now()
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    // Best-effort: call the local AetherBrowser chat endpoint (Ollama-backed).
    // Falls back to demo responses when the API isn't running.
    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMsg.content,
          model: 'local',
          mode,
          active_file_name: activeFileName,
          active_file_content: activeFileContent,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        const aiMsg: Message = {
          id: (Date.now() + 1).toString(),
          role: 'ai',
          content: (data && data.response) ? String(data.response) : '[No response]',
          timestamp: Date.now(),
        };
        setMessages(prev => [...prev, aiMsg]);
        setIsTyping(false);
        return;
      }
    } catch {
      // ignore and fall back
    }

    // Demo fallback (offline-friendly)
    setTimeout(() => {
      let response = "I'm not sure how to help with that yet.";

      const lowerInput = userMsg.content.toLowerCase();

      if (lowerInput.includes('help') || lowerInput.includes('what')) {
        response = "I can explain the current file, help you write a new function, or run governance-safe tasks via the terminal (ops/vault/trust).";
      } else if (lowerInput.includes('explain') && activeFileName) {
        response = `Currently, you are looking at **${activeFileName}**.\n\nAsk: “summarize this file” or “suggest next steps”.`;
      } else if (lowerInput.includes('fix') || lowerInput.includes('debug')) {
        response = "Debug flow: reproduce → isolate smallest failing case → inspect inputs/outputs → propose one change → retest.";
      } else if (lowerInput.includes('security') || lowerInput.includes('test')) {
        response = "Run: `ops tests` in the terminal (requires local API server).";
      } else {
        response = `Received: "${userMsg.content}".\n\nTo connect this panel to real model calls, start: python scripts/aetherbrowser/api_server.py`;
      }

      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: response,
        timestamp: Date.now(),
      };

      setMessages(prev => [...prev, aiMsg]);
      setIsTyping(false);
    }, 900);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ x: 400, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 400, opacity: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
          className="fixed md:relative right-0 top-14 md:top-0 h-[calc(100vh-3.5rem)] md:h-full w-full md:w-80 bg-slate-900 border-l border-slate-800 shadow-xl flex flex-col z-30"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-900">
            <div className="flex items-center gap-2">
              <div className="p-1.5 bg-blue-600/20 rounded-md">
                <Sparkles className="w-4 h-4 text-blue-400" />
              </div>
              <div>
                <h3 className="font-semibold text-sm text-slate-200">AI Architect</h3>
                <div className="flex items-center gap-1.5">
                   <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                   <span className="text-[10px] text-slate-400 uppercase tracking-wider">{mode} Mode</span>
                </div>
              </div>
            </div>
            <button 
              onClick={onClose}
              className="p-1 hover:bg-slate-800 rounded-md text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#1a1a1a]">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
              >
                <div className={`
                  flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center
                  ${msg.role === 'ai' ? 'bg-blue-600/20 text-blue-400' : 'bg-slate-700 text-slate-300'}
                `}>
                  {msg.role === 'ai' ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
                </div>
                
                <div className={`
                  max-w-[85%] rounded-lg p-3 text-sm leading-relaxed
                  ${msg.role === 'ai' 
                    ? 'bg-slate-800 text-slate-300 border border-slate-700' 
                    : 'bg-blue-600 text-white shadow-md'}
                `}>
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                </div>
              </div>
            ))}
            
            {isTyping && (
              <div className="flex gap-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-600/20 text-blue-400 flex items-center justify-center">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 flex items-center gap-2">
                   <Loader2 className="w-3 h-3 animate-spin text-slate-500" />
                   <span className="text-xs text-slate-500">Thinking...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-4 border-t border-slate-800 bg-slate-900">
            <form onSubmit={handleSend} className="relative">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask me anything..."
                className="w-full bg-slate-950 border border-slate-800 rounded-lg py-3 pl-4 pr-10 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-all"
              />
              <button
                type="submit"
                disabled={!input.trim() || isTyping}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-blue-500 hover:text-blue-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
            <div className="mt-2 text-center">
               <p className="text-[10px] text-slate-600">
                 AI can make mistakes. Review generated code.
               </p>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
