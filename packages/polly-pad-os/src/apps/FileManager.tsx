import React, { useState, useEffect } from 'react';
import { useOS } from '@/os/OSStore';
import { FS } from '@/utils/fs';
import type { FileNode } from '@/types';
import { Folder, File, ArrowLeft, Home, Plus, Trash2, Edit3, RefreshCw } from 'lucide-react';

export default function FileManager({ windowId }: { windowId: string }) {
  const { setWindowTitle } = useOS();
  const [currentDir, setCurrentDir] = useState<string>('user');
  const [files, setFiles] = useState<FileNode[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [newName, setNewName] = useState('');
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [showNewMenu, setShowNewMenu] = useState(false);

  const loadFiles = () => {
    const children = FS.getChildren(currentDir);
    setFiles(children);
  };

  useEffect(() => {
    loadFiles();
    const node = FS.getNode(currentDir);
    setWindowTitle(windowId, node ? `Files - ${node.name}` : 'Files');
  }, [currentDir, setWindowTitle, windowId]);

  const navigateUp = () => {
    const node = FS.getNode(currentDir);
    if (node?.parentId) setCurrentDir(node.parentId);
  };

  const navigateTo = (id: string) => {
    const node = FS.getNode(id);
    if (node?.type === 'directory') {
      setCurrentDir(id);
      setSelectedFile(null);
    }
  };

  const createNew = (type: 'file' | 'directory') => {
    const baseName = type === 'directory' ? 'New Folder' : 'New File';
    let name = baseName;
    let counter = 1;
    while (FS.exists(currentDir, name)) {
      name = `${baseName} ${counter}`;
      counter++;
    }
    FS.create(currentDir, name, type);
    loadFiles();
    setShowNewMenu(false);
  };

  const deleteSelected = () => {
    if (selectedFile) {
      FS.delete(selectedFile);
      setSelectedFile(null);
      loadFiles();
    }
  };

  const startRename = () => {
    if (selectedFile) {
      const node = FS.getNode(selectedFile);
      if (node) {
        setNewName(node.name);
        setRenamingId(selectedFile);
      }
    }
  };

  const confirmRename = () => {
    if (renamingId && newName.trim()) {
      FS.rename(renamingId, newName.trim());
      setRenamingId(null);
      loadFiles();
    }
  };

  const pathParts = [];
  let curr = currentDir;
  while (curr) {
    const node = FS.getNode(curr);
    if (!node) break;
    pathParts.unshift({ id: node.id, name: node.name });
    if (node.parentId === null) break;
    curr = node.parentId;
  }

  const formatSize = (bytes?: number) => {
    if (!bytes) return '-';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80">
      {/* Toolbar */}
      <div className="flex items-center gap-1 px-2 py-1.5 border-b border-blue-500/10 bg-[#111d2e]">
        <button
          onClick={navigateUp}
          className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/60 hover:text-blue-200 transition-colors"
          title="Up"
        >
          <ArrowLeft size={15} />
        </button>
        <button
          onClick={() => setCurrentDir('user')}
          className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/60 hover:text-blue-200 transition-colors"
          title="Home"
        >
          <Home size={15} />
        </button>
        <button
          onClick={loadFiles}
          className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/60 hover:text-blue-200 transition-colors"
          title="Refresh"
        >
          <RefreshCw size={15} />
        </button>
        <div className="w-px h-5 bg-blue-500/10 mx-1" />
        <div className="flex items-center gap-0.5 text-xs flex-1 overflow-hidden">
          {pathParts.map((part, idx) => (
            <React.Fragment key={part.id}>
              {idx > 0 && <span className="text-blue-400/20 mx-0.5">/</span>}
              <button
                onClick={() => navigateTo(part.id)}
                className="px-1.5 py-0.5 rounded hover:bg-blue-500/15 text-blue-300/50 hover:text-blue-200 transition-colors truncate"
              >
                {part.name}
              </button>
            </React.Fragment>
          ))}
        </div>
        <div className="w-px h-5 bg-blue-500/10 mx-1" />
        <div className="relative">
          <button
            onClick={() => setShowNewMenu(!showNewMenu)}
            className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/60 hover:text-blue-200 transition-colors"
            title="New"
          >
            <Plus size={15} />
          </button>
          {showNewMenu && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setShowNewMenu(false)} />
              <div className="absolute right-0 top-full mt-1 bg-[#162032] border border-blue-500/20 rounded-lg shadow-xl py-1 z-50 min-w-[140px]">
                <button
                  onClick={() => createNew('directory')}
                  className="w-full text-left px-3 py-1.5 text-xs hover:bg-blue-500/20 text-blue-200/70 transition-colors"
                >
                  New Folder
                </button>
                <button
                  onClick={() => createNew('file')}
                  className="w-full text-left px-3 py-1.5 text-xs hover:bg-blue-500/20 text-blue-200/70 transition-colors"
                >
                  New File
                </button>
              </div>
            </>
          )}
        </div>
        <button
          onClick={deleteSelected}
          disabled={!selectedFile}
          className="p-1.5 rounded hover:bg-red-500/20 text-blue-300/60 hover:text-red-400 transition-colors disabled:opacity-30"
          title="Delete"
        >
          <Trash2 size={15} />
        </button>
        <button
          onClick={startRename}
          disabled={!selectedFile}
          className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/60 hover:text-blue-200 transition-colors disabled:opacity-30"
          title="Rename"
        >
          <Edit3 size={15} />
        </button>
      </div>

      {/* File List */}
      <div className="flex-1 overflow-y-auto">
        <div className="grid grid-cols-[auto_1fr_100px_120px] gap-x-3 px-3 py-1.5 text-[10px] uppercase tracking-wider text-blue-400/30 border-b border-blue-500/5">
          <span></span>
          <span>Name</span>
          <span>Size</span>
          <span>Modified</span>
        </div>
        {files.length === 0 && (
          <div className="flex flex-col items-center justify-center h-40 text-blue-400/20 text-sm">
            <Folder size={32} />
            <p className="mt-2">This folder is empty</p>
          </div>
        )}
        {files.map((file) => (
          <div
            key={file.id}
            className={`grid grid-cols-[auto_1fr_100px_120px] gap-x-3 px-3 py-1.5 text-xs items-center cursor-pointer transition-colors ${
              selectedFile === file.id ? 'bg-blue-500/15' : 'hover:bg-blue-500/5'
            }`}
            onClick={() => setSelectedFile(file.id)}
            onDoubleClick={() => navigateTo(file.id)}
          >
            <span className="text-blue-400/50">
              {file.type === 'directory' ? <Folder size={16} /> : <File size={16} />}
            </span>
            {renamingId === file.id ? (
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onBlur={confirmRename}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') confirmRename();
                  if (e.key === 'Escape') setRenamingId(null);
                }}
                className="bg-blue-500/10 border border-blue-500/30 rounded px-1 py-0.5 text-xs outline-none"
                autoFocus
              />
            ) : (
              <span className="truncate">{file.name}</span>
            )}
            <span className="text-blue-300/30">{formatSize(file.size)}</span>
            <span className="text-blue-300/30">
              {new Date(file.modifiedAt).toLocaleDateString()}
            </span>
          </div>
        ))}
      </div>

      {/* Status Bar */}
      <div className="px-3 py-1 text-[10px] text-blue-400/30 border-t border-blue-500/10 bg-[#111d2e]">
        {files.length} items
      </div>
    </div>
  );
}
