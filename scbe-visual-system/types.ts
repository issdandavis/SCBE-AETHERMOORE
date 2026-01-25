/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import { LucideIcon } from 'lucide-react';

declare global {
    var html2canvas: (element: HTMLElement, options?: any) => Promise<HTMLCanvasElement>;
}

export type AppId = 'home' | 'mail' | 'slides' | 'snake' | 'folder' | 'notepad' | 'automator' | 'code' | 'sudoku' | 'wordle';

export interface DesktopItem {
    id: string;
    name: string;
    type: 'app' | 'folder';
    icon: LucideIcon;
    appId?: AppId;
    contents?: DesktopItem[];
    bgColor?: string;
    notepadInitialContent?: string;
}

export interface Point {
    x: number;
    y: number;
}

export type Stroke = Point[];

export interface Email {
    id: number;
    from: string;
    subject: string;
    preview: string;
    body: string;
    time: string;
    unread: boolean;
}

export type ToolAction = 
    | { type: 'DELETE_ITEM'; itemId: string }
    | { type: 'EXPLODE_FOLDER'; folderId: string }
    | { type: 'EXPLAIN_ITEM'; itemId: string }
    | { type: 'NONE' };