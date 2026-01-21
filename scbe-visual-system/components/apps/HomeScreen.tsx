/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import React from 'react';
import { DesktopItem } from '../../types';

interface HomeScreenProps {
    items: (DesktopItem | null)[];
    onLaunch: (item: DesktopItem) => void;
}

export const HomeScreen: React.FC<HomeScreenProps> = ({ items, onLaunch }) => {
    return (
        <div className="h-full w-full p-8 grid grid-cols-[repeat(auto-fill,minmax(110px,1fr))] gap-6 content-start justify-items-center overflow-y-auto overscroll-y-contain">
            {items.map((item, index) => {
                if (!item) {
                    // Render an invisible placeholder to maintain grid gap
                    return <div key={`gap-${index}`} className="w-28 h-[7rem]" />;
                }
                return (
                    <button
                        key={item.id}
                        onClick={() => onLaunch(item)}
                        className="flex flex-col items-center justify-start gap-3 p-2 w-28 rounded-xl hover:bg-white/10 transition-colors group"
                        title={item.name}
                    >
                        {/* Gentler 3D Effect: Reduced shadow opacity/spread, subtler inner shadows, lighter border */}
                        <div className={`relative w-20 h-20 ${item.bgColor || 'bg-zinc-700'} rounded-[22px] flex items-center justify-center shadow-[0_4px_8px_-4px_rgba(0,0,0,0.2),inset_0_1px_0.5px_rgba(255,255,255,0.15),inset_0_-1px_2px_rgba(0,0,0,0.1)] group-hover:scale-105 transition-transform duration-300 ease-out border-t border-white/10 overflow-hidden`}>
                             {/* Gentler Glossy Overlay */}
                            <div className="absolute inset-0 bg-[radial-gradient(at_top_left,_rgba(255,255,255,0.15)_0%,_transparent_70%)] pointer-events-none" />
                            
                            <item.icon className="w-10 h-10 text-white relative z-10 drop-shadow-[0_1px_2px_rgba(0,0,0,0.15)]" />
                        </div>
                        <span className="text-sm text-white font-medium text-center truncate w-full px-1 drop-shadow-md [text-shadow:_0_1px_2px_rgb(0_0_0_/_40%)]">
                            {item.name}
                        </span>
                    </button>
                );
            })}
        </div>
    );
};