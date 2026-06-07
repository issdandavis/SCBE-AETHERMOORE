import React, { useState } from 'react';
import { useOS } from '@/os/OSStore';
import { FS } from '@/utils/fs';
import { Save, FolderOpen, FilePlus } from 'lucide-react';

export default function TextEditor({ windowId, data }: { windowId: string; data?: any }) {
  const { setWindowTitle } = useOS();
  const [content, setContent] = useState(data?.content || '');
  const [fileId, setFileId] = useState<string | null>(data?.fileId || null);
  const [fileName, setFileName] = useState(data?.fileName || 'Untitled');
  const [showOpen, setShowOpen] = useState(false);
  const [openDir, setOpenDir] = useState('user');

  const handleSave = () => {
    if (fileId) {
      FS.write(fileId, content);
    } else {
      const name = prompt('Enter file name:', fileName);
      if (name) {
        const node = FS.create('user', name, 'file', content);
        setFileId(node.id);
        setFileName(name);
        setWindowTitle(windowId, name);
      }
    }
  };

  const handleNew = () => {
    setContent('');
    setFileId(null);
    setFileName('Untitled');
    setWindowTitle(windowId, 'Text Editor');
  };

  const handleOpenFile = (id: string, name: string) => {
    const file = FS.getNode(id);
    if (file && file.type === 'file') {
      setContent(file.content || '');
      setFileId(id);
      setFileName(name);
      setWindowTitle(windowId, name);
      setShowOpen(false);
    }
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926]">
      <div className="flex items-center gap-1 px-2 py-1.5 border-b border-blue-500/10 bg-[#111d2e]">
        <button
          onClick={handleNew}
          className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/60 hover:text-blue-200 transition-colors"
          title="New"
        >
          <FilePlus size={15} />
        </button>
        <button
          onClick={() => setShowOpen(!showOpen)}
          className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/60 hover:text-blue-200 transition-colors"
          title="Open"
        >
          <FolderOpen size={15} />
        </button>
        <button
          onClick={handleSave}
          className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/60 hover:text-blue-200 transition-colors"
          title="Save"
        >
          <Save size={15} />
        </button>
        <span className="text-xs text-blue-300/40 ml-2">{fileName}</span>
      </div>

      {showOpen && (
        <div className="absolute top-10 left-2 right-2 bottom-2 bg-[#111d2e] border border-blue-500/20 rounded-lg shadow-2xl z-20 p-4 overflow-auto">
          <h3 className="text-sm text-blue-200 mb-3">Open File</h3>
          {FS.getChildren(openDir)
            .filter((c) => c.type === 'file')
            .map((f) => (
              <button
                key={f.id}
                onClick={() => handleOpenFile(f.id, f.name)}
                className="w-full text-left px-3 py-2 text-xs text-blue-200/70 hover:bg-blue-500/15 rounded transition-colors"
              >
                {f.name}
              </button>
            ))}
          {FS.getChildren(openDir).filter((c) => c.type === 'file').length === 0 && (
            <p className="text-xs text-blue-300/30">No files found</p>
          )}
          <button
            onClick={() => setShowOpen(false)}
            className="mt-3 px-3 py-1.5 text-xs bg-blue-500/20 rounded hover:bg-blue-500/30 text-blue-200 transition-colors"
          >
            Cancel
          </button>
        </div>
      )}

      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        className="flex-1 bg-[#0d1926] text-blue-100/80 p-3 text-sm font-mono resize-none outline-none border-none"
        spellCheck={false}
      />
    </div>
  );
}
