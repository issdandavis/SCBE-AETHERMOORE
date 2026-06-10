import React, { useState, useEffect } from 'react';
import {
  User,
  Plus,
  Search,
  Phone,
  Mail,
  Trash2,
  Download,
  Upload,
  Copy,
  Check,
} from 'lucide-react';

interface Contact {
  id: string;
  name: string;
  email: string;
  phone: string;
  color: string;
}
const STORAGE_KEY = 'linuxos_contacts';
const COLORS = [
  'bg-blue-500/20 text-blue-300',
  'bg-green-500/20 text-green-300',
  'bg-yellow-500/20 text-yellow-300',
  'bg-red-500/20 text-red-300',
  'bg-purple-500/20 text-purple-300',
  'bg-pink-500/20 text-pink-300',
];

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

export default function Contacts() {
  const [contacts, setContacts] = useState<Contact[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch {
      /* ignore */
    }
    return [
      {
        id: '1',
        name: 'Alice Johnson',
        email: 'alice@example.com',
        phone: '+1 555-0101',
        color: COLORS[0],
      },
      {
        id: '2',
        name: 'Bob Smith',
        email: 'bob@example.com',
        phone: '+1 555-0102',
        color: COLORS[1],
      },
      {
        id: '3',
        name: 'Carol Williams',
        email: 'carol@example.com',
        phone: '+1 555-0103',
        color: COLORS[2],
      },
    ];
  });
  const [search, setSearch] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [newContact, setNewContact] = useState({ name: '', email: '', phone: '' });
  const [copiedField, setCopiedField] = useState<string | null>(null);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(contacts));
  }, [contacts]);

  const filtered = contacts.filter(
    (c) =>
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.email.toLowerCase().includes(search.toLowerCase()) ||
      c.phone.includes(search)
  );

  const add = () => {
    if (!newContact.name.trim()) return;
    setContacts([
      ...contacts,
      {
        ...newContact,
        id: Date.now().toString(),
        color: COLORS[Math.floor(Math.random() * COLORS.length)],
      },
    ]);
    setNewContact({ name: '', email: '', phone: '' });
    setShowAdd(false);
  };

  const remove = (id: string) => setContacts(contacts.filter((c) => c.id !== id));

  const copy = (text: string, field: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 1500);
  };

  const exportContacts = () => {
    const vCardData = contacts
      .map(
        (c) => `BEGIN:VCARD\nVERSION:3.0\nFN:${c.name}\nEMAIL:${c.email}\nTEL:${c.phone}\nEND:VCARD`
      )
      .join('\n');
    const blob = new Blob([vCardData], { type: 'text/vcard' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'contacts.vcf';
    a.click();
    URL.revokeObjectURL(url);
  };

  const importContacts = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.vcf,.json';
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (ev) => {
        try {
          const text = ev.target?.result as string;
          if (file.name.endsWith('.json')) {
            const imported = JSON.parse(text);
            if (Array.isArray(imported)) setContacts((prev) => [...imported, ...prev]);
          }
        } catch {
          /* ignore */
        }
      };
      reader.readAsText(file);
    };
    input.click();
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-blue-500/10">
        <User size={14} className="text-blue-400" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search contacts..."
          className="flex-1 bg-transparent text-xs outline-none placeholder-blue-300/20"
        />
        <button
          onClick={importContacts}
          className="p-1.5 rounded hover:bg-blue-500/20 text-blue-400 transition-colors"
          title="Import"
        >
          <Upload size={14} />
        </button>
        <button
          onClick={exportContacts}
          className="p-1.5 rounded hover:bg-blue-500/20 text-blue-400 transition-colors"
          title="Export vCard"
        >
          <Download size={14} />
        </button>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="p-1.5 rounded hover:bg-blue-500/20 text-blue-400"
        >
          <Plus size={14} />
        </button>
      </div>
      {showAdd && (
        <div className="px-3 py-2 border-b border-blue-500/10 bg-[#111d2e] space-y-1.5">
          <input
            value={newContact.name}
            onChange={(e) => setNewContact({ ...newContact, name: e.target.value })}
            onKeyDown={(e) => e.key === 'Enter' && add()}
            placeholder="Name *"
            className="w-full bg-[#162032] border border-blue-500/10 rounded-lg px-2 py-1 text-xs outline-none focus:border-blue-500/30"
          />
          <input
            value={newContact.email}
            onChange={(e) => setNewContact({ ...newContact, email: e.target.value })}
            placeholder="Email"
            className="w-full bg-[#162032] border border-blue-500/10 rounded-lg px-2 py-1 text-xs outline-none focus:border-blue-500/30"
          />
          <input
            value={newContact.phone}
            onChange={(e) => setNewContact({ ...newContact, phone: e.target.value })}
            placeholder="Phone"
            className="w-full bg-[#162032] border border-blue-500/10 rounded-lg px-2 py-1 text-xs outline-none focus:border-blue-500/30"
          />
          <button
            onClick={add}
            className="px-3 py-1 rounded-lg bg-blue-500/20 text-blue-200 text-xs hover:bg-blue-500/30"
          >
            Add Contact
          </button>
        </div>
      )}
      <div className="flex-1 overflow-y-auto">
        {filtered.map((c) => (
          <div
            key={c.id}
            className="flex items-center gap-3 px-3 py-2.5 border-b border-blue-500/5 hover:bg-blue-500/5 transition-colors group"
          >
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${c.color}`}
            >
              {getInitials(c.name)}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs text-blue-200/70 truncate">{c.name}</div>
              {c.email && <div className="text-[10px] text-blue-300/30 truncate">{c.email}</div>}
            </div>
            <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
              {c.email && (
                <button
                  onClick={() => copy(c.email, `email-${c.id}`)}
                  className="p-1 rounded hover:bg-blue-500/20 text-blue-300/30 hover:text-blue-300 transition-colors"
                >
                  {copiedField === `email-${c.id}` ? (
                    <Check size={11} className="text-green-400" />
                  ) : (
                    <Mail size={11} />
                  )}
                </button>
              )}
              {c.phone && (
                <button
                  onClick={() => copy(c.phone, `phone-${c.id}`)}
                  className="p-1 rounded hover:bg-blue-500/20 text-blue-300/30 hover:text-blue-300 transition-colors"
                >
                  {copiedField === `phone-${c.id}` ? (
                    <Check size={11} className="text-green-400" />
                  ) : (
                    <Phone size={11} />
                  )}
                </button>
              )}
              <button
                onClick={() => remove(c.id)}
                className="p-1 rounded hover:bg-red-500/20 text-blue-300/20 hover:text-red-400 transition-colors"
              >
                <Trash2 size={11} />
              </button>
            </div>
          </div>
        ))}
        {filtered.length === 0 && (
          <div className="text-center text-xs text-blue-400/20 py-8">No contacts found</div>
        )}
      </div>
    </div>
  );
}
