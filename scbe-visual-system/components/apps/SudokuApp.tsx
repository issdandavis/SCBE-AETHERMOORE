/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import React, { useState } from 'react';
import { RotateCcw, Lightbulb, CheckCircle2 } from 'lucide-react';

const INITIAL_BOARD = [
    [5, 3, 0, 0, 7, 0, 0, 0, 0],
    [6, 0, 0, 1, 9, 5, 0, 0, 0],
    [0, 9, 8, 0, 0, 0, 0, 6, 0],
    [8, 0, 0, 0, 6, 0, 0, 0, 3],
    [4, 0, 0, 8, 0, 3, 0, 0, 1],
    [7, 0, 0, 0, 2, 0, 0, 0, 6],
    [0, 6, 0, 0, 0, 0, 2, 8, 0],
    [0, 0, 0, 4, 1, 9, 0, 0, 5],
    [0, 0, 0, 0, 8, 0, 0, 7, 9]
];

export const SudokuApp: React.FC = () => {
    const [board, setBoard] = useState(INITIAL_BOARD);
    const [selected, setSelected] = useState<[number, number] | null>(null);

    const handleCellClick = (r: number, c: number) => {
        if (INITIAL_BOARD[r][c] !== 0) return;
        setSelected([r, c]);
    };

    const handleNumberClick = (n: number) => {
        if (!selected) return;
        const [r, c] = selected;
        const newBoard = board.map(row => [...row]);
        newBoard[r][c] = n;
        setBoard(newBoard);
    };

    return (
        <div className="h-full w-full bg-white flex flex-col items-center p-6 text-zinc-900">
            <div className="w-full max-w-sm flex justify-between items-center mb-8">
                <h2 className="text-xl font-black italic tracking-tighter uppercase">Daily Sudoku</h2>
                <div className="flex gap-2">
                    <button className="p-2 hover:bg-zinc-100 rounded-lg"><RotateCcw size={18} /></button>
                    <button className="p-2 hover:bg-zinc-100 rounded-lg text-amber-500"><Lightbulb size={18} /></button>
                </div>
            </div>

            <div className="grid grid-cols-9 border-2 border-zinc-900 w-full max-w-sm aspect-square">
                {board.map((row, r) => row.map((cell, c) => (
                    <div 
                        key={`${r}-${c}`}
                        onClick={() => handleCellClick(r, c)}
                        className={`border border-zinc-200 flex items-center justify-center text-lg font-black transition-colors cursor-pointer
                            ${INITIAL_BOARD[r][c] !== 0 ? 'bg-zinc-50 text-zinc-400' : 'bg-white text-zinc-900'}
                            ${selected?.[0] === r && selected?.[1] === c ? 'bg-sky-100 ring-2 ring-sky-500 z-10' : ''}
                            ${(c + 1) % 3 === 0 && c < 8 ? 'border-r-2 border-r-zinc-900' : ''}
                            ${(r + 1) % 3 === 0 && r < 8 ? 'border-b-2 border-b-zinc-900' : ''}
                        `}
                    >
                        {cell !== 0 ? cell : ''}
                    </div>
                )))}
            </div>

            <div className="grid grid-cols-9 gap-1 w-full max-w-sm mt-10">
                {[1, 2, 3, 4, 5, 6, 7, 8, 9].map(n => (
                    <button 
                        key={n}
                        onClick={() => handleNumberClick(n)}
                        className="aspect-square bg-zinc-900 text-white rounded-lg font-black text-sm hover:scale-105 active:scale-95 transition-transform"
                    >
                        {n}
                    </button>
                ))}
            </div>

            <button className="mt-auto w-full max-w-sm py-4 bg-emerald-600 text-white rounded-2xl font-black uppercase italic tracking-widest flex items-center justify-center gap-3">
                <CheckCircle2 size={20} /> Submit Board
            </button>
        </div>
    );
};