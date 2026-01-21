/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import React from 'react';
import { DesktopItem } from '../../types';
import { FileText } from 'lucide-react';

interface FolderViewProps {
    folder: DesktopItem;
}

export const FolderView: React.FC<FolderViewProps> = ({ folder }) => {
    return (
        <div className="h-full w-full bg-zinc-50 flex flex-col text-zinc-800 p-4 overflow-y-auto overscroll-y-contain">
             {/* Simulated random text */}
            <div className="mb-6 p-4 bg-white border border-zinc-200 rounded-lg shadow-sm">
                <div className="flex items-center gap-2 mb-2 text-zinc-500 font-medium uppercase text-[10px] tracking-wider">
                    <FileText size={14} /> README.txt
                </div>
                <p className="text-zinc-600 text-sm leading-relaxed">
                    This folder contains project assets and documentation. 
                    Ensure all sensitive data is encrypted before sharing.
                    Updated: Oct 26, 2023.
                </p>
            </div>

            <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider mb-3">
                Contents ({folder.contents?.length || 0})
            </h3>
            
            <div className="grid grid-cols-4 gap-2 content-start">
                {folder.contents?.map(item => (
                    <div key={item.id} className="flex flex-col items-center gap-1.5 p-2 hover:bg-zinc-200/50 rounded-lg cursor-pointer transition-colors group">
                        {/* Gentler 3D effect for small icons */}
                        <div className={`relative w-12 h-12 ${item.bgColor || 'bg-zinc-500'} rounded-xl flex items-center justify-center text-white shadow-[0_1px_3px_-1px_rgba(0,0,0,0.2),inset_0_1px_0.5px_rgba(255,255,255,0.2),inset_0_-1px_2px_rgba(0,0,0,0.1)] group-hover:scale-105 transition-transform duration-200 ease-out border-t border-white/10 overflow-hidden`}>
                             {/* Gentler Glossy Overlay (Scaled down) */}
                            <div className="absolute inset-0 bg-[radial-gradient(at_top_left,_rgba(255,255,255,0.2)_0%,_transparent_70%)] pointer-events-none" />
                            <item.icon size={24} className="relative z-10 drop-shadow-[0_1px_1px_rgba(0,0,0,0.1)]" />
                        </div>
                        <span className="text-xs text-center truncate w-full font-medium text-zinc-700 group-hover:text-zinc-900">{item.name}</span>
                    </div>
                ))}
                {(!folder.contents || folder.contents.length === 0) && (
                     <div className="col-span-full text-zinc-400 italic py-4 text-center text-sm">
                        Empty
                    </div>
                )}
            </div>
        </div>
    );
};