/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 *
 * AppStoreApp \u2014 categorized launcher for every GeoShell tile.
 * Reads ``apps-registry.json`` via ``loadCategories()`` and emits a
 * ``onLaunch(item)`` callback when the user picks a tile.
 */

import React, { useMemo, useState } from 'react';
import type { DesktopItem } from '../../types';
import { loadCategories, getRegistryMeta } from '../../lib/apps-registry-loader';

interface AppStoreAppProps {
    onLaunch: (item: DesktopItem) => void;
}

export const AppStoreApp: React.FC<AppStoreAppProps> = ({ onLaunch }) => {
    const categories = useMemo(loadCategories, []);
    const meta = useMemo(getRegistryMeta, []);
    const [filter, setFilter] = useState('');

    const filtered = useMemo(() => {
        if (!filter.trim()) return categories;
        const needle = filter.toLowerCase();
        return categories
            .map((cat) => ({
                ...cat,
                items: cat.items.filter((i) =>
                    i.name.toLowerCase().includes(needle) ||
                    i.id.toLowerCase().includes(needle) ||
                    (i.appId ?? '').toLowerCase().includes(needle),
                ),
            }))
            .filter((cat) => cat.items.length > 0);
    }, [categories, filter]);

    return (
        <div className="h-full w-full bg-black text-white overflow-y-auto">
            <header className="sticky top-0 bg-black/95 backdrop-blur border-b border-white/10 px-6 py-4 flex items-center justify-between gap-4 z-10">
                <div>
                    <div className="text-xs uppercase tracking-widest text-white/50">{meta.schemaVersion}</div>
                    <div className="text-xl font-semibold">{meta.shellName} \u00b7 App Store</div>
                </div>
                <input
                    type="text"
                    placeholder="Search apps, games, services\u2026"
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                    className="bg-zinc-900 border border-white/10 rounded-lg px-3 py-2 text-sm w-64 focus:outline-none focus:border-sky-500"
                />
            </header>

            <main className="px-6 py-6 space-y-8">
                {filtered.map((cat) => (
                    <section key={cat.id}>
                        <h2 className="text-sm uppercase tracking-widest text-white/40 mb-3">{cat.label}</h2>
                        <div className="grid grid-cols-[repeat(auto-fill,minmax(160px,1fr))] gap-4">
                            {cat.items.map((item) => (
                                <button
                                    key={item.id}
                                    onClick={() => onLaunch(item)}
                                    className="flex flex-col items-start gap-3 p-4 rounded-2xl border border-white/10 hover:border-sky-500 hover:bg-white/5 transition text-left"
                                >
                                    <div className={`w-12 h-12 rounded-xl ${item.bgColor ?? 'bg-zinc-700'} flex items-center justify-center`}>
                                        <item.icon className="w-6 h-6 text-white" />
                                    </div>
                                    <div>
                                        <div className="text-sm font-semibold">{item.name}</div>
                                        <div className="text-[11px] text-white/50 font-mono">{item.appId}</div>
                                    </div>
                                    {item.service?.description && (
                                        <div className="text-[11px] text-white/40 line-clamp-2">
                                            {item.service.description}
                                        </div>
                                    )}
                                </button>
                            ))}
                        </div>
                    </section>
                ))}
                {filtered.length === 0 && (
                    <div className="text-white/40 text-sm">No tiles match "{filter}".</div>
                )}
            </main>
        </div>
    );
};
