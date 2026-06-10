import React, { useState, useMemo } from 'react';
import { useOS } from './OSStore';
import { getAppCapability, isLaunchSurface } from './appCapabilities';
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
  Power,
  User,
  X,
  LayoutGrid,
  Puzzle,
  Monitor,
  Wrench,
  Bot,
  Shield,
  ShieldCheck,
  GitBranch,
  Fingerprint,
  Eye,
  Radio,
  Atom,
  Orbit,
  Zap,
  Box,
  Layers,
  Sigma,
} from 'lucide-react';

const categoryIcons: Record<string, React.ReactNode> = {
  Tools: <Wrench size={16} />,
  System: <Monitor size={16} />,
  Productivity: <LayoutGrid size={16} />,
  Games: <Puzzle size={16} />,
  Media: <Video size={16} />,
  Utilities: <Wrench size={16} />,
  Development: <Code size={16} />,
  Ecosystem: <ShieldCheck size={16} />,
};

const categoryOrder = [
  'Tools',
  'System',
  'Productivity',
  'Internet',
  'Media',
  'Development',
  'Utilities',
  'Games',
  'Ecosystem',
];

const iconMap: Record<string, React.ReactNode> = {
  FolderOpen: <FolderOpen size={22} />,
  Terminal: <Terminal size={22} />,
  FileText: <FileText size={22} />,
  Globe: <Globe size={22} />,
  Calculator: <Calculator size={22} />,
  Settings: <Settings size={22} />,
  Gamepad2: <Gamepad2 size={22} />,
  Grid3x3: <Grid3x3 size={22} />,
  Music: <Music size={22} />,
  Image: <Image size={22} />,
  Paintbrush: <Paintbrush size={22} />,
  Code: <Code size={22} />,
  Search: <Search size={22} />,
  Palette: <Palette size={22} />,
  KeyRound: <KeyRound size={22} />,
  BookOpen: <BookOpen size={22} />,
  Mail: <Mail size={22} />,
  MessageCircle: <MessageCircle size={22} />,
  StickyNote: <StickyNote size={22} />,
  Crown: <Crown size={22} />,
  Bomb: <Bomb size={22} />,
  Clock: <Clock size={22} />,
  Calendar: <Calendar size={22} />,
  Activity: <Activity size={22} />,
  Table: <Table size={22} />,
  CheckSquare: <CheckSquare size={22} />,
  Mic: <Mic size={22} />,
  CloudSun: <CloudSun size={22} />,
  BarChart3: <BarChart3 size={22} />,
  HardDrive: <HardDrive size={22} />,
  Camera: <Camera size={22} />,
  Timer: <Timer size={22} />,
  Hourglass: <Hourglass size={22} />,
  TrendingUp: <TrendingUp size={22} />,
  Newspaper: <Newspaper size={22} />,
  Video: <Video size={22} />,
  QrCode: <QrCode size={22} />,
  Languages: <Languages size={22} />,
  // Additional icons
  Divide: <Calculator size={22} />,
  Footprints: <Gamepad2 size={22} />,
  Bird: <Globe size={22} />,
  Layers: <LayoutGrid size={22} />,
  Sigma: <Sigma size={22} />,
  UserX: <User size={22} />,
  Type: <FileText size={22} />,
  Braces: <Code size={22} />,
  Regex: <Search size={22} />,
  FileCode: <FileText size={22} />,
  FileJson: <FileText size={22} />,
  ArrowLeftRight: <Globe size={22} />,
  PaintBucket: <Palette size={22} />,
  Rss: <Newspaper size={22} />,
  Pencil: <FileText size={22} />,
  BookMarked: <BookOpen size={22} />,
  Fingerprint: <KeyRound size={22} />,
  GitCompare: <Code size={22} />,
  Binary: <Calculator size={22} />,
  HeartPulse: <Activity size={22} />,
  Keyboard: <KeyboardIcon size={22} />,
  CircleDot: <Grid3x3 size={22} />,
  RotateCcw: <Settings size={22} />,
  Club: <Gamepad2 size={22} />,
  HelpCircle: <Search size={22} />,
  Gauge: <Activity size={22} />,
  Network: <Globe size={22} />,
  Presentation: <Monitor size={22} />,
  Bot: <Bot size={22} />,
  Shield: <Shield size={22} />,
  ShieldCheck: <ShieldCheck size={22} />,
  GitBranch: <GitBranch size={22} />,
  Eye: <Eye size={22} />,
  Radio: <Radio size={22} />,
  Atom: <Atom size={22} />,
  Orbit: <Orbit size={22} />,
  Zap: <Zap size={22} />,
  Box: <Box size={22} />,
  MonitorPlay: <Monitor size={22} />,
  RectangleHorizontal: <Video size={22} />,
  Brain: <LayoutGrid size={22} />,
  Grid2x2: <Grid3x3 size={22} />,
  XCircle: <X size={22} />,
};

function KeyboardIcon({ size }: { size: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="2" y="4" width="20" height="16" rx="2" />
      <path d="M6 8h.01M10 8h.01M14 8h.01M18 8h.01M8 12h.01M12 12h.01M16 12h.01M7 16h10" />
    </svg>
  );
}

export default function StartMenu() {
  const { appRegistry, openApp, setStartMenuOpen, startMenuOpen } = useOS();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [showBacklog, setShowBacklog] = useState(false);

  const apps = useMemo(() => {
    const list = Array.from(appRegistry.values()).filter(
      (app) => showBacklog || isLaunchSurface(app.id)
    );
    if (!searchQuery && !selectedCategory) return list;
    return list.filter((app) => {
      const matchesSearch =
        !searchQuery || app.name.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesCategory = !selectedCategory || app.category === selectedCategory;
      return matchesSearch && matchesCategory;
    });
  }, [appRegistry, searchQuery, selectedCategory, showBacklog]);

  const categories = useMemo(() => {
    const cats = new Set<string>();
    apps.forEach((app) => cats.add(app.category));
    return categoryOrder.filter((c) => cats.has(c));
  }, [apps]);

  const appsByCategory = useMemo(() => {
    const map: Record<string, typeof apps> = {};
    apps.forEach((app) => {
      if (!map[app.category]) map[app.category] = [];
      map[app.category].push(app);
    });
    return map;
  }, [apps]);

  if (!startMenuOpen) return null;

  return (
    <>
      <div className="fixed inset-0 z-40" onClick={() => setStartMenuOpen(false)} />
      <div className="fixed bottom-14 left-2 z-50 w-[680px] max-h-[650px] bg-[#0f1d2e]/95 border border-blue-500/15 rounded-2xl shadow-2xl backdrop-blur-2xl flex flex-col overflow-hidden">
        {/* Search Bar */}
        <div className="p-4 pb-2">
          <div className="relative">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-blue-400/50"
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search apps..."
              className="w-full bg-blue-500/5 border border-blue-500/15 rounded-xl pl-9 pr-4 py-2.5 text-sm text-blue-100 placeholder-blue-400/30 outline-none focus:border-blue-500/40 focus:bg-blue-500/10 transition-all"
              autoFocus
            />
          </div>
        </div>

        {/* Category Filters */}
        <div className="px-4 flex gap-1 overflow-x-auto pb-2">
          <button
            onClick={() => setSelectedCategory(null)}
            className={`px-3 py-1 rounded-lg text-xs transition-all whitespace-nowrap ${
              !selectedCategory
                ? 'bg-blue-500/25 text-blue-200 border border-blue-400/30'
                : 'text-blue-300/50 hover:bg-blue-500/10'
            }`}
          >
            All
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(selectedCategory === cat ? null : cat)}
              className={`px-3 py-1 rounded-lg text-xs transition-all whitespace-nowrap flex items-center gap-1.5 ${
                selectedCategory === cat
                  ? 'bg-blue-500/25 text-blue-200 border border-blue-400/30'
                  : 'text-blue-300/50 hover:bg-blue-500/10'
              }`}
            >
              {categoryIcons[cat]}
              {cat}
            </button>
          ))}
          <button
            onClick={() => setShowBacklog(!showBacklog)}
            className={`px-3 py-1 rounded-lg text-xs transition-all whitespace-nowrap ${
              showBacklog
                ? 'bg-amber-500/20 text-amber-200 border border-amber-400/30'
                : 'text-blue-300/50 hover:bg-blue-500/10'
            }`}
          >
            {showBacklog ? 'Hide backlog' : 'Show all apps'}
          </button>
        </div>

        {/* Apps Grid */}
        <div className="flex-1 overflow-y-auto px-4 pb-4 custom-scrollbar">
          {searchQuery ? (
            <div className="grid grid-cols-4 gap-1.5 mt-2">
              {apps.map((app) => (
                <AppTile
                  key={app.id}
                  app={app}
                  status={getAppCapability(app.id).status}
                  onClick={() => openApp(app.id)}
                />
              ))}
            </div>
          ) : (
            <div className="space-y-3 mt-2">
              {(selectedCategory ? [selectedCategory] : categories).map((cat) => (
                <div key={cat}>
                  <div className="text-[10px] uppercase tracking-wider text-blue-400/40 font-semibold mb-1.5 px-1">
                    {cat}
                  </div>
                  <div className="grid grid-cols-4 gap-1.5">
                    {(appsByCategory[cat] || []).map((app) => (
                      <AppTile
                        key={app.id}
                        app={app}
                        status={getAppCapability(app.id).status}
                        onClick={() => openApp(app.id)}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {apps.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-blue-400/30">
              <Search size={32} />
              <p className="mt-2 text-sm">No apps found</p>
            </div>
          )}
        </div>

        {/* User Bar */}
        <div className="border-t border-blue-500/10 px-4 py-2.5 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white text-xs font-bold">
              U
            </div>
            <span className="text-sm text-blue-200/80">User</span>
          </div>
          <button
            onClick={() => setStartMenuOpen(false)}
            className="p-1.5 rounded-lg text-blue-300/40 hover:bg-red-500/20 hover:text-red-400 transition-colors"
          >
            <Power size={16} />
          </button>
        </div>
      </div>
    </>
  );
}

function AppTile({
  app,
  status,
  onClick,
}: {
  app: { id: string; name: string; icon: string };
  status: ReturnType<typeof getAppCapability>['status'];
  onClick: () => void;
}) {
  const statusClasses = {
    'download-ready': 'bg-sky-500/15 text-sky-200',
    local: 'bg-emerald-500/15 text-emerald-200',
    real: 'bg-blue-500/20 text-blue-100',
  };

  return (
    <button
      onClick={onClick}
      className="flex flex-col items-center justify-center gap-1.5 p-2.5 rounded-xl hover:bg-blue-500/15 transition-all duration-150 group text-center"
    >
      <div className="text-blue-300/70 group-hover:text-blue-200 transition-colors">
        {iconMap[app.icon] || <FolderOpen size={22} />}
      </div>
      <span className="text-[10px] text-blue-200/60 group-hover:text-blue-100 leading-tight">
        {app.name}
      </span>
      {status !== 'real' && (
        <span className={`rounded px-1.5 py-0.5 text-[9px] ${statusClasses[status]}`}>
          {status}
        </span>
      )}
    </button>
  );
}
