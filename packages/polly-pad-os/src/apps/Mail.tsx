import React, { useState } from 'react';
import { Mail, Star, Trash2, Send, Inbox } from 'lucide-react';

const DEMO_EMAILS = [
  {
    id: '1',
    from: 'admin@linuxos.web',
    subject: 'Welcome to SCBE Tool Desktop',
    preview: 'Thank you for trying out SCBE Tool Desktop...',
    starred: true,
    read: false,
  },
  {
    id: '2',
    from: 'newsletter@web.dev',
    subject: 'Weekly Web Dev Tips',
    preview: "Here are this week's best practices...",
    starred: false,
    read: true,
  },
  {
    id: '3',
    from: 'noreply@github.com',
    subject: 'Security Alert',
    preview: 'New sign-in detected from your account...',
    starred: false,
    read: true,
  },
  {
    id: '4',
    from: 'support@linuxos.web',
    subject: 'Getting Started Guide',
    preview: 'Here is a quick guide to help you...',
    starred: true,
    read: false,
  },
];

export default function MailApp() {
  const [emails, setEmails] = useState(DEMO_EMAILS);
  const [selected, setSelected] = useState<string | null>(null);
  const [compose, setCompose] = useState(false);
  const [to, setTo] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [tab, setTab] = useState<'inbox' | 'starred'>('inbox');

  const toggleStar = (id: string) =>
    setEmails((prev) => prev.map((e) => (e.id === id ? { ...e, starred: !e.starred } : e)));
  const filtered = tab === 'inbox' ? emails : emails.filter((e) => e.starred);
  const selectedEmail = emails.find((e) => e.id === selected);

  return (
    <div className="w-full h-full flex bg-[#0d1926] text-blue-100/80">
      <div className="w-12 border-r border-blue-500/10 bg-[#111d2e] flex flex-col items-center py-3 gap-2">
        <button
          onClick={() => setCompose(true)}
          className="p-2 rounded-lg bg-blue-500/20 text-blue-200 hover:bg-blue-500/30"
        >
          <Send size={16} />
        </button>
        <button
          onClick={() => setTab('inbox')}
          className={`p-2 rounded-lg transition-colors ${tab === 'inbox' ? 'bg-blue-500/15 text-blue-200' : 'text-blue-300/30 hover:text-blue-200'}`}
        >
          <Inbox size={16} />
        </button>
        <button
          onClick={() => setTab('starred')}
          className={`p-2 rounded-lg transition-colors ${tab === 'starred' ? 'bg-blue-500/15 text-blue-200' : 'text-blue-300/30 hover:text-blue-200'}`}
        >
          <Star size={16} />
        </button>
      </div>
      <div className="w-56 border-r border-blue-500/10 overflow-y-auto">
        {filtered.map((e) => (
          <button
            key={e.id}
            onClick={() => setSelected(e.id)}
            className={`w-full text-left px-3 py-2 border-b border-blue-500/5 transition-colors ${selected === e.id ? 'bg-blue-500/10' : 'hover:bg-blue-500/5'} ${!e.read ? 'border-l-2 border-l-blue-500' : ''}`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs text-blue-200/70 truncate">{e.from}</span>
            </div>
            <div
              className={`text-xs truncate ${!e.read ? 'text-blue-200 font-medium' : 'text-blue-200/40'}`}
            >
              {e.subject}
            </div>
            <div className="text-[10px] text-blue-300/30 truncate">{e.preview}</div>
          </button>
        ))}
      </div>
      <div className="flex-1 p-4">
        {compose ? (
          <div className="h-full flex flex-col">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm text-blue-200">New Message</h3>
              <button onClick={() => setCompose(false)} className="text-xs text-blue-300/40">
                Cancel
              </button>
            </div>
            <input
              value={to}
              onChange={(e) => setTo(e.target.value)}
              placeholder="To"
              className="bg-[#162032] border border-blue-500/10 rounded-lg px-3 py-1.5 text-xs mb-2 outline-none"
            />
            <input
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Subject"
              className="bg-[#162032] border border-blue-500/10 rounded-lg px-3 py-1.5 text-xs mb-2 outline-none"
            />
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Message..."
              className="flex-1 bg-[#162032] border border-blue-500/10 rounded-lg p-3 text-xs resize-none outline-none"
            />
            <button
              onClick={() => {
                setCompose(false);
                setTo('');
                setSubject('');
                setBody('');
              }}
              className="mt-2 px-4 py-2 rounded-lg bg-blue-500/20 text-blue-200 text-xs hover:bg-blue-500/30 self-end"
            >
              Send
            </button>
          </div>
        ) : selectedEmail ? (
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm text-blue-200 font-medium">{selectedEmail.subject}</h3>
              <div className="flex gap-1">
                <button
                  onClick={() => toggleStar(selectedEmail.id)}
                  className={`p-1 rounded ${selectedEmail.starred ? 'text-yellow-400' : 'text-blue-300/20'}`}
                >
                  <Star size={14} />
                </button>
                <button className="p-1 rounded text-blue-300/20 hover:text-red-400">
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
            <div className="text-xs text-blue-300/40 mb-3">From: {selectedEmail.from}</div>
            <div className="text-sm text-blue-200/70">{selectedEmail.preview}</div>
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-blue-400/20">
            <Mail size={48} />
            <p className="text-sm mt-2">Select an email</p>
          </div>
        )}
      </div>
    </div>
  );
}
