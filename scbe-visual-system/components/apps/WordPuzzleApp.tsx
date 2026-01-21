/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import React, { useState } from 'react';
import { Type as TypeIcon, Delete } from 'lucide-react';

export const WordPuzzleApp: React.FC = () => {
    const [guesses, setGuesses] = useState<string[]>(['GEMINI', '', '', '', '', '']);
    const [currentGuess, setCurrentGuess] = useState(0);

    return (
        <div className="h-full w-full bg-zinc-50 flex flex-col items-center p-8 text-zinc-900">
            <div className="flex flex-col items-center gap-2 mb-12">
                <TypeIcon size={40} className="text-amber-600" />
                <h2 className="text-2xl font-black italic tracking-tighter uppercase">Daily Wordle</h2>
                <span className="text-[10px] font-black text-zinc-400 uppercase tracking-[0.3em]">Issue #402</span>
            </div>

            <div className="flex flex-col gap-2 mb-auto">
                {guesses.map((guess, i) => (
                    <div key={i} className="flex gap-2">
                        {[0, 1, 2, 3, 4, 5].map(j => {
                            const char = guess[j] || '';
                            let bgColor = 'bg-white border-zinc-200';
                            let textColor = 'text-zinc-900';
                            
                            if (i === 0) {
                                if (j === 0 || j === 4) bgColor = 'bg-emerald-500 border-emerald-600 text-white';
                                else if (j === 1 || j === 3) bgColor = 'bg-amber-500 border-amber-600 text-white';
                                else bgColor = 'bg-zinc-400 border-zinc-500 text-white';
                            }

                            return (
                                <div key={j} className={`w-12 h-12 md:w-14 md:h-14 border-2 rounded-xl flex items-center justify-center text-2xl font-black uppercase transition-all ${bgColor} ${textColor}`}>
                                    {char}
                                </div>
                            );
                        })}
                    </div>
                ))}
            </div>

            <div className="w-full max-w-md mt-12 grid grid-cols-10 gap-1.5">
                {['Q','W','E','R','T','Y','U','I','O','P','A','S','D','F','G','H','J','K','L','Z','X','C','V','B','N','M'].map(key => (
                    <button key={key} className="bg-white border border-zinc-200 p-3 rounded-lg text-xs font-black shadow-sm active:bg-zinc-100 active:scale-95 transition-all">
                        {key}
                    </button>
                ))}
                <button className="col-span-2 bg-zinc-900 text-white p-3 rounded-lg text-[10px] font-black uppercase tracking-widest">Enter</button>
                <button className="col-span-2 bg-zinc-200 text-zinc-600 p-3 rounded-lg flex items-center justify-center"><Delete size={16} /></button>
            </div>
        </div>
    );
};