/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import React, { useState } from 'react';
import { Mail, Star, Trash2, Inbox, Send, Archive, ChevronLeft } from 'lucide-react';
import { Email } from '../../types';

interface MailAppProps {
    emails: Email[];
}

export const MailApp: React.FC<MailAppProps> = ({ emails }) => {
    const [selectedEmailId, setSelectedEmailId] = useState<number | null>(null);
    const selectedEmail = emails.find(e => e.id === selectedEmailId);

    React.useEffect(() => {
        if (selectedEmailId !== null && !selectedEmail) {
            setSelectedEmailId(null);
        }
    }, [emails, selectedEmailId, selectedEmail]);

    return (
        <div className="h-full w-full bg-[#0a0a0f] flex text-zinc-200 relative">
            {/* Sidebar - Hidden on mobile if viewing an email */}
            <div className={`${selectedEmail ? 'hidden lg:flex' : 'flex'} w-20 lg:w-56 bg-black/40 border-r border-zinc-800/50 flex-col overflow-y-auto overscroll-y-contain backdrop-blur-xl z-10 shrink-0`}>
                <div className="p-6 font-black text-xl flex items-center gap-3 text-sky-400 border-b border-white/5 mb-4">
                    <Mail size={24} className="shrink-0" /> <span className="hidden lg:inline uppercase tracking-tighter italic">InkMail</span>
                </div>
                <nav className="flex flex-col gap-2 px-3">
                    <button className="flex items-center gap-4 px-4 py-3 bg-sky-500/10 text-sky-400 rounded-2xl text-sm font-black uppercase tracking-widest border border-sky-500/20">
                        <Inbox size={20} />
                        <span className="hidden lg:inline">Inbox</span>
                        {emails.filter(e => e.unread).length > 0 && (
                            <span className="ml-auto bg-sky-500 text-black text-[10px] px-2 py-0.5 rounded-full font-black">
                                {emails.filter(e => e.unread).length}
                            </span>
                        )}
                    </button>
                    {['Starred', 'Sent', 'Archive', 'Trash'].map((item, i) => (
                         <button key={item} className="flex items-center gap-4 px-4 py-3 text-zinc-500 hover:bg-white/5 hover:text-white rounded-2xl text-sm font-bold transition-all">
                            {i === 0 ? <Star size={20} /> : i === 1 ? <Send size={20} /> : i === 2 ? <Archive size={20} /> : <Trash2 size={20} />}
                            <span className="hidden lg:inline">{item}</span>
                        </button>
                    ))}
                </nav>
            </div>

            {/* Email List */}
            <div className={`${selectedEmail ? 'hidden md:block' : 'block'} w-full md:w-96 border-r border-zinc-800/50 overflow-y-auto overscroll-y-contain bg-black/20 relative z-0`}>
                {emails.length === 0 ? (
                    <div className="p-12 text-center text-zinc-600 flex flex-col items-center">
                        <Inbox size={64} className="mb-6 opacity-10" />
                        <p className="font-bold uppercase tracking-widest text-xs italic">Encrypted Inbox Empty</p>
                    </div>
                ) : (
                    <div className="flex flex-col">
                        {emails.map(email => (
                            <div
                                key={email.id}
                                onClick={() => setSelectedEmailId(email.id)}
                                className={`p-6 border-b border-white/5 cursor-pointer hover:bg-white/5 transition-all relative group ${selectedEmailId === email.id ? 'bg-sky-500/5' : ''}`}
                            >
                                {email.unread && <div className="absolute left-2 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-sky-500 shadow-[0_0_8px_rgba(56,189,248,0.5)]" />}
                                <div className="flex justify-between items-baseline mb-2">
                                    <span className={`text-sm truncate pr-2 ${email.unread ? 'text-white font-black' : 'text-zinc-400 font-bold'}`}>{email.from}</span>
                                    <span className="text-[10px] text-zinc-600 font-mono flex-shrink-0">{email.time}</span>
                                </div>
                                <div className={`text-sm mb-1 truncate tracking-tight ${email.unread ? 'font-bold text-zinc-100' : 'text-zinc-500'}`}>{email.subject}</div>
                                <div className="text-[11px] text-zinc-600 truncate leading-relaxed line-clamp-1">{email.preview}</div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Email View */}
            <div className={`${selectedEmail ? 'block' : 'hidden md:block'} flex-1 bg-black/10 overflow-y-auto overscroll-y-contain relative`}>
                {selectedEmail ? (
                    <div className="p-6 md:p-12 max-w-4xl mx-auto">
                        <button 
                            className="md:hidden mb-8 flex items-center gap-2 text-sky-400 text-sm font-black uppercase tracking-widest bg-sky-400/10 px-5 py-3 rounded-2xl border border-sky-400/20 active:scale-95 transition-transform" 
                            onClick={() => setSelectedEmailId(null)}
                        >
                            <ChevronLeft size={20} /> Back to Inbox
                        </button>
                        
                        <div className="mb-10">
                            <h2 className="text-3xl md:text-5xl font-black mb-6 text-white tracking-tighter leading-tight italic">{selectedEmail.subject}</h2>
                            <div className="flex items-center justify-between p-6 bg-white/5 rounded-3xl border border-white/5">
                                <div className="flex items-center gap-4">
                                    <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-sky-400 to-indigo-600 flex items-center justify-center font-black text-black">
                                        {selectedEmail.from[0]}
                                    </div>
                                    <div>
                                        <div className="font-black text-lg text-white tracking-tight">{selectedEmail.from}</div>
                                        <div className="text-zinc-500 text-xs font-bold uppercase tracking-widest">To: me@aethermore.com</div>
                                    </div>
                                </div>
                                <div className="text-zinc-500 text-xs font-mono hidden sm:block">{selectedEmail.time}</div>
                            </div>
                        </div>

                        <div className="text-zinc-300 leading-relaxed text-lg font-normal whitespace-pre-wrap px-2">
                            {selectedEmail.body}
                        </div>

                        <div className="mt-16 pt-10 border-t border-white/5 flex gap-4">
                            <button className="px-8 py-3 bg-white text-black font-black uppercase tracking-widest rounded-2xl text-xs hover:scale-105 transition-transform">Reply</button>
                            <button className="px-8 py-3 bg-zinc-800 text-white font-black uppercase tracking-widest rounded-2xl text-xs hover:bg-zinc-700 transition-colors">Forward</button>
                        </div>
                    </div>
                ) : (
                    <div className="h-full flex flex-col items-center justify-center text-zinc-700 p-8 text-center">
                        <div className="w-24 h-24 rounded-full bg-white/5 border border-white/5 flex items-center justify-center mb-6">
                            <Mail size={40} className="opacity-20" />
                        </div>
                        <h3 className="font-black uppercase tracking-widest text-sm mb-2">Secure Viewer</h3>
                        <p className="text-xs font-medium max-w-xs leading-relaxed">Select an encrypted transmission to decrypt and view contents on the high-security console.</p>
                    </div>
                )}
            </div>
        </div>
    );
};