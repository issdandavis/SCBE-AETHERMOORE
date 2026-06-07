import type { FileNode } from '@/types';

const STORAGE_KEY = 'linuxos_fs';

const defaultFS: FileNode[] = [
  {
    id: 'root',
    name: '/',
    type: 'directory',
    parentId: null,
    createdAt: Date.now(),
    modifiedAt: Date.now(),
  },
  {
    id: 'home',
    name: 'home',
    type: 'directory',
    parentId: 'root',
    createdAt: Date.now(),
    modifiedAt: Date.now(),
  },
  {
    id: 'user',
    name: 'user',
    type: 'directory',
    parentId: 'home',
    createdAt: Date.now(),
    modifiedAt: Date.now(),
  },
  {
    id: 'desktop',
    name: 'Desktop',
    type: 'directory',
    parentId: 'user',
    createdAt: Date.now(),
    modifiedAt: Date.now(),
  },
  {
    id: 'documents',
    name: 'Documents',
    type: 'directory',
    parentId: 'user',
    createdAt: Date.now(),
    modifiedAt: Date.now(),
  },
  {
    id: 'downloads',
    name: 'Downloads',
    type: 'directory',
    parentId: 'user',
    createdAt: Date.now(),
    modifiedAt: Date.now(),
  },
  {
    id: 'music',
    name: 'Music',
    type: 'directory',
    parentId: 'user',
    createdAt: Date.now(),
    modifiedAt: Date.now(),
  },
  {
    id: 'pictures',
    name: 'Pictures',
    type: 'directory',
    parentId: 'user',
    createdAt: Date.now(),
    modifiedAt: Date.now(),
  },
  {
    id: 'videos',
    name: 'Videos',
    type: 'directory',
    parentId: 'user',
    createdAt: Date.now(),
    modifiedAt: Date.now(),
  },
  {
    id: 'system',
    name: 'System',
    type: 'directory',
    parentId: 'root',
    createdAt: Date.now(),
    modifiedAt: Date.now(),
  },
  {
    id: 'apps',
    name: 'Applications',
    type: 'directory',
    parentId: 'root',
    createdAt: Date.now(),
    modifiedAt: Date.now(),
  },
  {
    id: 'welcome',
    name: 'Welcome.txt',
    type: 'file',
    parentId: 'documents',
    content:
      'Welcome to LinuxOS Web!\n\nThis is a fully functional web-based Linux replica with 50+ applications.\n\nExplore the desktop, open apps, play games, and enjoy the experience!\n\nFeatures:\n- Desktop environment with draggable icons\n- Window management (drag, resize, minimize, maximize)\n- Virtual file system with persistence\n- 50+ fully functional applications\n- Terminal with real commands\n- Games, productivity tools, media players\n- And much more!\n\nGet started by clicking the Start Menu.',
    createdAt: Date.now(),
    modifiedAt: Date.now(),
    size: 512,
    mimeType: 'text/plain',
  },
  {
    id: 'readme',
    name: 'README.md',
    type: 'file',
    parentId: 'user',
    content:
      '# LinuxOS Web\n\nA web-based Linux replica built with React and TypeScript.\n\n## Quick Start\n- Click the Start button to open the app menu\n- Double-click desktop icons to open apps\n- Use the terminal for command-line operations\n- Right-click the desktop for context menu\n\nHave fun!',
    createdAt: Date.now(),
    modifiedAt: Date.now(),
    size: 256,
    mimeType: 'text/markdown',
  },
];

function loadFS(): FileNode[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) return JSON.parse(stored);
  } catch {
    /* ignore */
  }
  return [...defaultFS];
}

function saveFS(nodes: FileNode[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(nodes));
}

let fsNodes = loadFS();

export const FS = {
  getNodes: () => fsNodes,
  refresh: () => {
    fsNodes = loadFS();
  },

  getChildren: (parentId: string): FileNode[] => {
    return fsNodes.filter((n) => n.parentId === parentId);
  },

  getNode: (id: string): FileNode | undefined => {
    return fsNodes.find((n) => n.id === id);
  },

  getPath: (id: string): string => {
    const node = fsNodes.find((n) => n.id === id);
    if (!node) return '';
    if (node.parentId === null) return node.name;
    return FS.getPath(node.parentId) + (node.parentId === 'root' ? '' : '/') + node.name;
  },

  create: (
    parentId: string,
    name: string,
    type: 'file' | 'directory',
    content?: string
  ): FileNode => {
    const node: FileNode = {
      id: 'node_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9),
      name,
      type,
      parentId,
      content: type === 'file' ? content || '' : undefined,
      createdAt: Date.now(),
      modifiedAt: Date.now(),
      size: type === 'file' ? new Blob([content || '']).size : 0,
      mimeType: type === 'file' ? getMimeType(name) : undefined,
    };
    fsNodes.push(node);
    saveFS(fsNodes);
    return node;
  },

  delete: (id: string): boolean => {
    const node = fsNodes.find((n) => n.id === id);
    if (!node) return false;
    if (node.id === 'root' || node.id === 'home' || node.id === 'user') return false;
    const children = fsNodes.filter((n) => n.parentId === id);
    children.forEach((c) => FS.delete(c.id));
    fsNodes = fsNodes.filter((n) => n.id !== id);
    saveFS(fsNodes);
    return true;
  },

  rename: (id: string, newName: string): boolean => {
    const node = fsNodes.find((n) => n.id === id);
    if (!node) return false;
    node.name = newName;
    node.modifiedAt = Date.now();
    if (node.type === 'file') {
      node.mimeType = getMimeType(newName);
    }
    saveFS(fsNodes);
    return true;
  },

  write: (id: string, content: string): boolean => {
    const node = fsNodes.find((n) => n.id === id);
    if (!node || node.type !== 'file') return false;
    node.content = content;
    node.modifiedAt = Date.now();
    node.size = new Blob([content]).size;
    saveFS(fsNodes);
    return true;
  },

  read: (id: string): string | undefined => {
    const node = fsNodes.find((n) => n.id === id);
    return node?.content;
  },

  exists: (parentId: string, name: string): boolean => {
    return fsNodes.some((n) => n.parentId === parentId && n.name === name);
  },

  findByPath: (path: string): FileNode | undefined => {
    if (path === '/' || path === '') return fsNodes.find((n) => n.id === 'root');
    const parts = path.split('/').filter(Boolean);
    let current = fsNodes.find((n) => n.id === 'root');
    for (const part of parts) {
      const child = fsNodes.find((n) => n.parentId === current?.id && n.name === part);
      if (!child) return undefined;
      current = child;
    }
    return current;
  },

  reset: () => {
    fsNodes = [...defaultFS.map((n) => ({ ...n }))];
    saveFS(fsNodes);
  },
};

function getMimeType(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  const map: Record<string, string> = {
    txt: 'text/plain',
    md: 'text/markdown',
    html: 'text/html',
    css: 'text/css',
    js: 'application/javascript',
    json: 'application/json',
    png: 'image/png',
    jpg: 'image/jpeg',
    jpeg: 'image/jpeg',
    gif: 'image/gif',
    svg: 'image/svg+xml',
    pdf: 'application/pdf',
    mp3: 'audio/mpeg',
    mp4: 'video/mp4',
    wav: 'audio/wav',
    ogg: 'audio/ogg',
    webm: 'video/webm',
    csv: 'text/csv',
    xml: 'application/xml',
    zip: 'application/zip',
    rar: 'application/x-rar-compressed',
    tar: 'application/x-tar',
    '7z': 'application/x-7z-compressed',
    exe: 'application/x-msdownload',
    doc: 'application/msword',
    docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    xls: 'application/vnd.ms-excel',
    xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    ppt: 'application/vnd.ms-powerpoint',
    pptx: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    odt: 'application/vnd.oasis.opendocument.text',
    ods: 'application/vnd.oasis.opendocument.spreadsheet',
    odp: 'application/vnd.oasis.opendocument.presentation',
    rtf: 'application/rtf',
    bmp: 'image/bmp',
    ico: 'image/x-icon',
    tiff: 'image/tiff',
    webp: 'image/webp',
    avi: 'video/x-msvideo',
    mov: 'video/quicktime',
    wmv: 'video/x-ms-wmv',
    flv: 'video/x-flv',
    mkv: 'video/x-matroska',
    m4a: 'audio/mp4',
    flac: 'audio/flac',
    aac: 'audio/aac',
    wma: 'audio/x-ms-wma',
  };
  return map[ext] || 'application/octet-stream';
}
