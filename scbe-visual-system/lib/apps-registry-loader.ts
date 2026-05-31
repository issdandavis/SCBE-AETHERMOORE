/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 *
 * Loads ``apps-registry.json`` and turns the data into typed ``DesktopItem``
 * tiles + categorized groups for the GeoShell App Store.
 *
 * Design rules:
 *  - Registry is data, not code. App.tsx must not hard-code tile lists.
 *  - Icons are resolved by string name from ``lucide-react``.
 *  - Unknown icon names fall back to ``Folder``.
 *  - The ``how_to_use`` tile keeps its prior NotepadApp seed content (legacy).
 */

import * as Lucide from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import registry from '../apps-registry.json';
import type { AppId, DesktopItem, ServiceBinding } from '../types';

interface RegistryTile {
    id: string;
    name: string;
    appId?: string;
    icon?: string;
    bgColor?: string;
    service?: ServiceBinding;
}

interface RegistryCategory {
    id: string;
    label: string;
    tiles: RegistryTile[];
}

interface RegistryShape {
    schema_version: string;
    shell_name: string;
    categories: RegistryCategory[];
}

const HOW_TO_USE_NOTE = `GEOSHELL — KINDLE EDITION

Optimized for E-Ink and Productivity.

GESTURES:
- Draw 'X' to close/delete
- Draw '?' to explain
- Draw arrows to move/explode

NEW IN GEOSHELL:
- App Store: discover and launch every SCBE app and game
- Spiral Word: collaborative editor (start spiral-word-app/app.py)
- GeoSeal Service: nested CLI HTTP service (uvicorn src.api.geoseal_service:app)
- IDE / Sudoku / Wordle / Automator (Zapier/Notion sync)`;

function resolveIcon(name: string | undefined): LucideIcon {
    if (!name) return (Lucide.Folder as unknown) as LucideIcon;
    const lookup = (Lucide as unknown as Record<string, LucideIcon | undefined>)[name];
    if (lookup) return lookup;
    return (Lucide.Folder as unknown) as LucideIcon;
}

function isAppId(value: string | undefined): value is AppId {
    if (!value) return false;
    const allowed: AppId[] = [
        'home', 'mail', 'slides', 'snake', 'folder', 'notepad', 'automator',
        'code', 'sudoku', 'wordle', 'security', 'cryptolab', 'defense',
        'agents', 'overseer', 'fleet', 'knowledge', 'pollypad', 'service',
        'appstore',
    ];
    return (allowed as string[]).includes(value);
}

function tileToDesktopItem(tile: RegistryTile, categoryId: string): DesktopItem {
    const item: DesktopItem = {
        id: tile.id,
        name: tile.name,
        type: 'app',
        icon: resolveIcon(tile.icon),
        appId: isAppId(tile.appId) ? tile.appId : 'notepad',
        bgColor: tile.bgColor ?? 'bg-zinc-700',
        category: categoryId,
    };
    if (tile.service) {
        item.service = tile.service;
    }
    if (tile.id === 'how_to_use') {
        item.notepadInitialContent = HOW_TO_USE_NOTE;
    }
    return item;
}

export interface CategoryView {
    id: string;
    label: string;
    items: DesktopItem[];
}

export function loadCategories(): CategoryView[] {
    const r = registry as unknown as RegistryShape;
    return r.categories.map((cat) => ({
        id: cat.id,
        label: cat.label,
        items: cat.tiles.map((t) => tileToDesktopItem(t, cat.id)),
    }));
}

export function loadDesktopItems(): DesktopItem[] {
    return loadCategories().flatMap((c) => c.items);
}

export function getRegistryMeta(): { shellName: string; schemaVersion: string } {
    const r = registry as unknown as RegistryShape;
    return { shellName: r.shell_name, schemaVersion: r.schema_version };
}

export function resolveServiceUrl(binding: ServiceBinding): string {
    const envName = binding.envUrl;
    if (envName && typeof process !== 'undefined' && process?.env?.[envName]) {
        return process.env[envName] as string;
    }
    return binding.defaultUrl;
}
