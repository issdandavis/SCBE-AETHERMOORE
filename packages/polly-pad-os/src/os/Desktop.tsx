import React, { useState, useCallback } from 'react';
import { useOS } from './OSStore';
import {
  FolderOpen,
  Terminal,
  FileText,
  Globe,
  Calculator,
  Settings,
  Gamepad2,
  Grid3x3,
  Music,
  Image,
  Paintbrush,
  Code,
  Search,
  Palette,
  KeyRound,
  BookOpen,
  Mail,
  MessageCircle,
  StickyNote,
  Crown,
  Bomb,
  Clock,
  Calendar,
  Activity,
  Table,
  CheckSquare,
  Mic,
  CloudSun,
  BarChart3,
  HardDrive,
  Camera,
  Timer,
  Hourglass,
  TrendingUp,
  Newspaper,
  Video,
  QrCode,
  Languages,
  Folder,
  Copy,
  Scissors,
  Trash2,
  RefreshCw,
} from 'lucide-react';

const iconMap: Record<string, React.ReactNode> = {
  FolderOpen: <FolderOpen size={40} />,
  Terminal: <Terminal size={40} />,
  FileText: <FileText size={40} />,
  Globe: <Globe size={40} />,
  Calculator: <Calculator size={40} />,
  Settings: <Settings size={40} />,
  Gamepad2: <Gamepad2 size={40} />,
  Grid3x3: <Grid3x3 size={40} />,
  Music: <Music size={40} />,
  Image: <Image size={40} />,
  Paintbrush: <Paintbrush size={40} />,
  Code: <Code size={40} />,
  Search: <Search size={40} />,
  Palette: <Palette size={40} />,
  KeyRound: <KeyRound size={40} />,
  BookOpen: <BookOpen size={40} />,
  Mail: <Mail size={40} />,
  MessageCircle: <MessageCircle size={40} />,
  StickyNote: <StickyNote size={40} />,
  Crown: <Crown size={40} />,
  Bomb: <Bomb size={40} />,
  Clock: <Clock size={40} />,
  Calendar: <Calendar size={40} />,
  Activity: <Activity size={40} />,
  Table: <Table size={40} />,
  CheckSquare: <CheckSquare size={40} />,
  Mic: <Mic size={40} />,
  CloudSun: <CloudSun size={40} />,
  BarChart3: <BarChart3 size={40} />,
  HardDrive: <HardDrive size={40} />,
  Camera: <Camera size={40} />,
  Timer: <Timer size={40} />,
  Hourglass: <Hourglass size={40} />,
  TrendingUp: <TrendingUp size={40} />,
  Newspaper: <Newspaper size={40} />,
  Video: <Video size={40} />,
  QrCode: <QrCode size={40} />,
  Languages: <Languages size={40} />,
};

export default function Desktop() {
  const { desktopIcons, openApp, focusWindow, windows, activeWindowId } = useOS();
  const [selectedIcon, setSelectedIcon] = useState<string | null>(null);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number } | null>(null);

  const handleDesktopClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === e.currentTarget) {
        setSelectedIcon(null);
        setContextMenu(null);
        if (activeWindowId) {
          const winEl = document.getElementById(`window-${activeWindowId}`);
          if (!winEl?.contains(e.target as Node)) {
            // Deselect windows
          }
        }
      }
    },
    [activeWindowId]
  );

  const handleIconDoubleClick = useCallback(
    (appId: string) => {
      openApp(appId);
      setSelectedIcon(null);
    },
    [openApp]
  );

  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY });
  }, []);

  return (
    <div
      className="absolute inset-0 pt-0 pb-12 select-none overflow-hidden"
      onClick={handleDesktopClick}
      onContextMenu={handleContextMenu}
      style={{
        background: 'linear-gradient(135deg, #0c1929 0%, #0f2037 30%, #132744 60%, #0d1e33 100%)',
      }}
    >
      {/* Animated background particles */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {Array.from({ length: 20 }).map((_, i) => (
          <div
            key={i}
            className="absolute rounded-full opacity-10"
            style={{
              width: 2 + Math.random() * 4,
              height: 2 + Math.random() * 4,
              background: '#60a5fa',
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animation: `float ${10 + Math.random() * 20}s linear infinite`,
              animationDelay: `${Math.random() * 10}s`,
            }}
          />
        ))}
      </div>

      {/* Desktop grid pattern */}
      <div
        className="absolute inset-0 opacity-[0.03] pointer-events-none"
        style={{
          backgroundImage:
            'linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)',
          backgroundSize: '50px 50px',
        }}
      />

      {/* Desktop Icons */}
      <div
        className="relative z-10 flex flex-col flex-wrap gap-2 p-4 h-full content-start"
        style={{ gap: '4px' }}
      >
        {desktopIcons.map((icon, idx) => (
          <div
            key={icon.id}
            className={`flex flex-col items-center justify-center w-24 h-28 rounded-lg cursor-pointer transition-all duration-150 group ${
              selectedIcon === icon.id
                ? 'bg-blue-500/30 border border-blue-400/50'
                : 'hover:bg-white/10 border border-transparent'
            }`}
            style={{ marginBottom: '4px' }}
            onClick={(e) => {
              e.stopPropagation();
              setSelectedIcon(icon.id);
            }}
            onDoubleClick={() => handleIconDoubleClick(icon.appId)}
          >
            <div
              className={`${selectedIcon === icon.id ? 'text-blue-300' : 'text-blue-200/80 group-hover:text-blue-200'}`}
            >
              {iconMap[icon.icon] || <FolderOpen size={40} />}
            </div>
            <span
              className={`mt-1 text-xs text-center px-1 rounded leading-tight max-w-full truncate ${
                selectedIcon === icon.id
                  ? 'bg-blue-500/50 text-white'
                  : 'text-blue-100/70 group-hover:text-blue-100'
              }`}
            >
              {icon.name}
            </span>
          </div>
        ))}
      </div>

      {/* Context Menu */}
      {contextMenu && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setContextMenu(null)} />
          <div
            className="fixed z-50 bg-[#162032]/95 border border-blue-500/20 rounded-lg shadow-2xl py-1 min-w-[180px] backdrop-blur-xl"
            style={{ left: contextMenu.x, top: contextMenu.y }}
          >
            <ContextMenuItem
              icon={<FolderOpen size={14} />}
              label="New Folder"
              onClick={() => setContextMenu(null)}
            />
            <ContextMenuItem
              icon={<FileText size={14} />}
              label="New Document"
              onClick={() => setContextMenu(null)}
            />
            <div className="border-t border-blue-500/10 my-1" />
            <ContextMenuItem
              icon={<RefreshCw size={14} />}
              label="Refresh"
              onClick={() => setContextMenu(null)}
            />
            <ContextMenuItem
              icon={<Settings size={14} />}
              label="Change Background"
              onClick={() => setContextMenu(null)}
            />
            <div className="border-t border-blue-500/10 my-1" />
            <ContextMenuItem
              icon={<Trash2 size={14} />}
              label="Clear Desktop"
              onClick={() => setContextMenu(null)}
            />
          </div>
        </>
      )}
    </div>
  );
}

function ContextMenuItem({
  icon,
  label,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      className="w-full flex items-center gap-2.5 px-3 py-1.5 text-sm text-blue-100/80 hover:bg-blue-500/20 hover:text-blue-50 transition-colors"
      onClick={onClick}
    >
      {icon}
      {label}
    </button>
  );
}
