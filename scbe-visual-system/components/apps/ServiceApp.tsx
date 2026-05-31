/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 *
 * ServiceApp renders an in-shell iframe for a nested HTTP service (Spiral
 * Word, GeoSeal, GeoSeal Docs). When the service URL is unreachable or no
 * env override is present, it shows a help panel with the start command.
 */

import React, { useEffect, useState } from 'react';
import { ExternalLink, RefreshCw, AlertTriangle } from 'lucide-react';
import type { DesktopItem } from '../../types';
import { resolveServiceUrl } from '../../lib/apps-registry-loader';

interface ServiceAppProps {
    item: DesktopItem;
}

export const ServiceApp: React.FC<ServiceAppProps> = ({ item }) => {
    const binding = item.service;
    const [reloadKey, setReloadKey] = useState(0);
    const [status, setStatus] = useState<'idle' | 'loading' | 'ok' | 'error'>('idle');

    if (!binding) {
        return (
            <div className="h-full w-full p-8 flex items-center justify-center text-white/70">
                Service binding missing for {item.name}.
            </div>
        );
    }
    const effectiveUrl = resolveServiceUrl(binding);

    useEffect(() => {
        setStatus('loading');
    }, [reloadKey, effectiveUrl]);

    if (binding.openInExternal) {
        return (
            <div className="h-full w-full p-8 flex flex-col items-center justify-center gap-4 text-white">
                <ExternalLink size={48} className="text-sky-400" />
                <div className="text-2xl font-semibold">{item.name}</div>
                <div className="text-sm text-white/60 text-center max-w-md">
                    {binding.description ?? 'This tile opens an external page.'}
                </div>
                <a
                    href={effectiveUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="px-4 py-2 bg-sky-600 hover:bg-sky-500 rounded-lg text-sm font-semibold"
                >
                    Open {effectiveUrl}
                </a>
            </div>
        );
    }

    return (
        <div className="h-full w-full flex flex-col bg-black text-white">
            <div className="px-3 py-2 border-b border-white/10 flex items-center justify-between text-xs">
                <span className="font-mono opacity-75 truncate">{effectiveUrl}</span>
                <div className="flex items-center gap-2">
                    {status === 'error' && (
                        <span className="flex items-center gap-1 text-amber-400">
                            <AlertTriangle size={12} /> service unreachable
                        </span>
                    )}
                    <button
                        type="button"
                        onClick={() => setReloadKey((k) => k + 1)}
                        className="p-1 rounded hover:bg-white/10"
                        title="Reload"
                    >
                        <RefreshCw size={14} />
                    </button>
                    <a
                        href={effectiveUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="p-1 rounded hover:bg-white/10"
                        title="Open in browser"
                    >
                        <ExternalLink size={14} />
                    </a>
                </div>
            </div>
            <div className="flex-1 relative">
                <iframe
                    key={reloadKey}
                    src={effectiveUrl}
                    title={item.name}
                    className="absolute inset-0 w-full h-full bg-white"
                    onLoad={() => setStatus('ok')}
                    onError={() => setStatus('error')}
                />
            </div>
            {binding.description && (
                <div className="px-3 py-2 border-t border-white/10 text-[11px] text-white/50">
                    {binding.description}
                </div>
            )}
        </div>
    );
};
