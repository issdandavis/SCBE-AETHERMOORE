import React, { useState, useRef, useEffect } from 'react';
import { Send, User, Bot, Trash2, Volume2, Copy, Clock } from 'lucide-react';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: number;
}

const STORAGE_KEY = 'linuxos_chat_history';

const KNOWLEDGE_BASE: Record<string, string | (() => string)> = {
  help: 'Available commands:\n• help - Show this message\n• time - Show current time\n• date - Show current date\n• calc <expr> - Calculate (e.g., calc 2+2)\n• echo <text> - Echo text back\n• flip - Flip a coin\n• roll - Roll a dice\n• joke - Tell a joke\n• clear - Clear chat',
  time: () => `Current time: ${new Date().toLocaleTimeString()}`,
  date: () =>
    `Today is ${new Date().toLocaleDateString('en', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}`,
  joke: () => {
    const jokes = [
      'Why do programmers prefer dark mode? Because light attracts bugs!',
      'Why did the developer go broke? Because he used up all his cache!',
      "How many programmers does it take to change a light bulb? None, that's a hardware problem!",
      "Why do Java developers wear glasses? Because they don't C#!",
      "What's a computer's favorite snack? Microchips!",
    ];
    return jokes[Math.floor(Math.random() * jokes.length)];
  },
  hello: 'Hello there! I\'m the SCBE demo assistant. Type "help" to see what I can do.',
  hi: 'Hi! How can I help you today?',
  hey: 'Hey there! Need any assistance?',
};

function resolveKnowledge(key: string): string | null {
  const val = KNOWLEDGE_BASE[key];
  if (!val) return null;
  return typeof val === 'string' ? val : val();
}

function processCommand(input: string): string | null {
  const text = input.trim().toLowerCase();
  const [cmd, ...args] = text.split(' ');
  const rest = args.join(' ');

  if (text === 'help') return resolveKnowledge('help');
  if (text === 'time') return resolveKnowledge('time');
  if (text === 'date') return resolveKnowledge('date');
  if (text === 'joke') return resolveKnowledge('joke');
  if (text === 'flip') return `🪙 ${Math.random() > 0.5 ? 'Heads' : 'Tails'}!`;
  if (text === 'roll') return `🎲 You rolled a ${Math.floor(Math.random() * 6) + 1}!`;
  if (text === 'clear') return '__CLEAR__';
  if (cmd === 'echo' && rest) return rest;
  if (cmd === 'calc' && rest) {
    try {
      // Safe evaluation
      const sanitized = rest.replace(/[^0-9+\-*/.()\s]/g, '');
      // eslint-disable-next-line no-new-func
      const result = new Function('return ' + sanitized)();
      return `${rest} = ${result}`;
    } catch {
      return 'Invalid calculation. Try: calc 2 + 2';
    }
  }
  // Knowledge base lookup
  for (const key of Object.keys(KNOWLEDGE_BASE)) {
    if (text.includes(key)) return resolveKnowledge(key);
  }
  return null;
}

const FALLBACK_RESPONSES = [
  'I\'m not sure I understand. Type "help" for available commands.',
  'Interesting! I\'m still learning. Try "help" to see what I can do.',
  'Got it. Is there anything else I can help with?',
  'I see. Type "help" for a list of commands I understand.',
];

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch {
      /* ignore */
    }
    return [
      {
        id: '1',
        text: 'Hello! I\'m the SCBE demo assistant. Type "help" to see what I can do.',
        sender: 'bot',
        timestamp: Date.now(),
      },
    ];
  });
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
  }, [messages]);

  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight);
  }, [messages]);

  const send = () => {
    if (!input.trim()) return;
    const userMsg: Message = {
      id: Date.now().toString(),
      text: input.trim(),
      sender: 'user',
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMsg]);
    const userText = input.trim();
    setInput('');

    setTimeout(
      () => {
        const result = processCommand(userText);
        if (result === '__CLEAR__') {
          setMessages([
            {
              id: Date.now().toString(),
              text: 'Chat cleared. Type "help" for commands.',
              sender: 'bot',
              timestamp: Date.now(),
            },
          ]);
          return;
        }
        const botText =
          result || FALLBACK_RESPONSES[Math.floor(Math.random() * FALLBACK_RESPONSES.length)];
        const botMsg: Message = {
          id: (Date.now() + 1).toString(),
          text: botText,
          sender: 'bot',
          timestamp: Date.now(),
        };
        setMessages((prev) => [...prev, botMsg]);
      },
      300 + Math.random() * 400
    );
  };

  const speak = (text: string) => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1;
      utterance.pitch = 1;
      window.speechSynthesis.speak(utterance);
    }
  };

  const clearChat = () => {
    setMessages([
      {
        id: Date.now().toString(),
        text: 'Chat cleared. Type "help" for commands.',
        sender: 'bot',
        timestamp: Date.now(),
      },
    ]);
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80">
      <div className="flex items-center justify-between px-3 py-2 border-b border-blue-500/10 bg-[#111d2e]">
        <div className="flex items-center gap-2">
          <Bot size={14} className="text-blue-400" />
          <span className="text-xs text-blue-200 font-semibold">SCBE Demo Assistant</span>
        </div>
        <button
          onClick={clearChat}
          className="p-1 rounded hover:bg-red-500/20 text-blue-300/30 hover:text-red-400 transition-colors"
          title="Clear chat"
        >
          <Trash2 size={12} />
        </button>
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'} gap-2`}
          >
            {msg.sender === 'bot' && (
              <div className="w-6 h-6 rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0 mt-1">
                <Bot size={12} className="text-blue-400" />
              </div>
            )}
            <div
              className={`max-w-[75%] px-3 py-2 rounded-xl text-xs leading-relaxed whitespace-pre-wrap ${msg.sender === 'user' ? 'bg-blue-500/20 text-blue-100 rounded-br-sm' : 'bg-[#162032] text-blue-200/70 rounded-bl-sm border border-blue-500/5'}`}
            >
              {msg.text}
              {msg.sender === 'bot' && (
                <div className="flex items-center gap-1 mt-1.5 pt-1 border-t border-blue-500/10">
                  <button
                    onClick={() => navigator.clipboard.writeText(msg.text)}
                    className="p-0.5 rounded hover:bg-blue-500/20 text-blue-400/30 hover:text-blue-300 transition-colors"
                    title="Copy"
                  >
                    <Copy size={9} />
                  </button>
                  <button
                    onClick={() => speak(msg.text)}
                    className="p-0.5 rounded hover:bg-blue-500/20 text-blue-400/30 hover:text-blue-300 transition-colors"
                    title="Speak"
                  >
                    <Volume2 size={9} />
                  </button>
                  <span className="text-[9px] text-blue-400/20 ml-auto flex items-center gap-0.5">
                    <Clock size={8} />
                    {new Date(msg.timestamp).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </div>
              )}
            </div>
            {msg.sender === 'user' && (
              <div className="w-6 h-6 rounded-full bg-blue-500/30 flex items-center justify-center flex-shrink-0 mt-1">
                <User size={12} className="text-blue-300" />
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="flex items-center gap-2 px-3 py-2 border-t border-blue-500/10 bg-[#111d2e]">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder="Type a message or command..."
          className="flex-1 bg-[#162032] border border-blue-500/15 rounded-xl px-3 py-2 text-xs outline-none focus:border-blue-500/30 transition-colors"
        />
        <button
          onClick={send}
          className="p-2 rounded-full bg-blue-500/20 text-blue-200 hover:bg-blue-500/30 transition-colors"
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  );
}
