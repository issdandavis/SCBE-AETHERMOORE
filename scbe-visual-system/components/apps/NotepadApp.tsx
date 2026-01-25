/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import React, { useState, useEffect, useRef } from 'react';

interface NotepadAppProps {
    id: string;
    initialContent?: string;
}

export const NotepadApp: React.FC<NotepadAppProps> = ({ id, initialContent = '' }) => {
    // Try to load existing content from storage, otherwise fall back to initialContent
    const [text, setText] = useState(() => {
        const saved = localStorage.getItem(`notepad-content-${id}`);
        return saved !== null ? saved : initialContent;
    });

    const textRef = useRef(text);

    // Keep ref in sync for the interval closure
    useEffect(() => {
        textRef.current = text;
    }, [text]);

    useEffect(() => {
        const saveToStorage = () => {
            localStorage.setItem(`notepad-content-${id}`, textRef.current);
            console.log(`[Notepad] Auto-saved content for ${id}`);
        };

        // Set up the auto-save interval (30 seconds)
        const intervalId = setInterval(saveToStorage, 30000);

        // Save on unmount to ensure latest changes are captured
        return () => {
            clearInterval(intervalId);
            saveToStorage();
        };
    }, [id]);

    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setText(e.target.value);
    };

    return (
        <div className="h-full w-full bg-zinc-900 text-zinc-300 flex flex-col relative">
            <textarea 
                className="flex-1 w-full h-full p-4 resize-none border-none focus:outline-none font-mono text-sm bg-transparent overflow-y-auto overscroll-y-contain"
                value={text}
                onChange={handleChange}
                spellCheck={false}
                placeholder="Start typing..."
            />
            <div className="absolute bottom-2 right-4 pointer-events-none">
                <span className="text-[10px] font-mono text-zinc-600 uppercase tracking-widest opacity-50">
                    Auto-save enabled (30s)
                </span>
            </div>
        </div>
    );
};