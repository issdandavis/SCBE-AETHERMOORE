
import React from 'react';
import { ChevronRight, ChevronDown, File, Folder, FolderOpen } from 'lucide-react';
import { FileNode } from '../data/initialFiles';

interface LeftSidebarProps {
  files: FileNode[];
  onFileSelect: (file: FileNode) => void;
  onToggleFolder: (folderId: string) => void;
  activeFileId?: string;
}

const FileTreeItem: React.FC<{
  node: FileNode;
  depth: number;
  onSelect: (file: FileNode) => void;
  onToggle: (id: string) => void;
  activeId?: string;
}> = ({ node, depth, onSelect, onToggle, activeId }) => {
  const isFolder = node.type === 'folder';
  const isActive = node.id === activeId;

  return (
    <div>
      <div
        className={`
          flex items-center gap-1.5 py-1 px-2 cursor-pointer select-none text-sm transition-colors
          ${isActive ? 'bg-blue-900/40 text-blue-300 border-l-2 border-blue-500' : 'hover:bg-slate-800 text-slate-400 hover:text-slate-200 border-l-2 border-transparent'}
        `}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
        onClick={() => isFolder ? onToggle(node.id) : onSelect(node)}
      >
        <span className="opacity-70">
          {isFolder ? (
            node.isOpen ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />
          ) : (
            <span className="w-3.5" />
          )}
        </span>
        
        <span className={`opacity-80 ${isFolder ? 'text-amber-400' : 'text-blue-400'}`}>
          {isFolder ? (
            node.isOpen ? <FolderOpen className="w-4 h-4" /> : <Folder className="w-4 h-4" />
          ) : (
            <File className="w-4 h-4" />
          )}
        </span>
        
        <span className="truncate">{node.name}</span>
      </div>

      {isFolder && node.isOpen && node.children && (
        <div>
          {node.children.map((child) => (
            <FileTreeItem
              key={child.id}
              node={child}
              depth={depth + 1}
              onSelect={onSelect}
              onToggle={onToggle}
              activeId={activeId}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export const LeftSidebar: React.FC<LeftSidebarProps> = ({ files, onFileSelect, onToggleFolder, activeFileId }) => {
  return (
    <div className="py-2">
      {files.map((node) => (
        <FileTreeItem
          key={node.id}
          node={node}
          depth={0}
          onSelect={onFileSelect}
          onToggle={onToggleFolder}
          activeId={activeFileId}
        />
      ))}
    </div>
  );
};
