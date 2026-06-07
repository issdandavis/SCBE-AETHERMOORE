import { lazy, Suspense } from 'react';
import type { AppDefinition } from '@/types';
import { useOS } from './OSStore';
import WindowComponent from './Window';

// Systematic imports for all apps
const appImports: Record<string, () => Promise<{ default: React.ComponentType<any> }>> = {
  files: () => import('@/apps/FileManager'),
  terminal: () => import('@/apps/Terminal'),
  multiagent: () => import('@/apps/MultiAgentTerminal'),
  texteditor: () => import('@/apps/TextEditor'),
  browser: () => import('@/apps/Browser'),
  calculator: () => import('@/apps/Calculator'),
  settings: () => import('@/apps/Settings'),
  calendar: () => import('@/apps/Calendar'),
  clock: () => import('@/apps/Clock'),
  taskmanager: () => import('@/apps/TaskManager'),
  search: () => import('@/apps/Search'),
  snake: () => import('@/apps/games/Snake'),
  tetris: () => import('@/apps/games/Tetris'),
  minesweeper: () => import('@/apps/games/Minesweeper'),
  tictactoe: () => import('@/apps/games/TicTacToe'),
  pong: () => import('@/apps/games/Pong'),
  breakout: () => import('@/apps/games/Breakout'),
  memory: () => import('@/apps/games/Memory'),
  sudoku: () => import('@/apps/games/Sudoku'),
  chess: () => import('@/apps/games/Chess'),
  wordle: () => import('@/apps/games/Wordle'),
  game2048: () => import('@/apps/games/Game2048'),
  dinorun: () => import('@/apps/games/DinoRun'),
  flappybird: () => import('@/apps/games/FlappyBird'),
  solitaire: () => import('@/apps/games/Solitaire'),
  hangman: () => import('@/apps/games/Hangman'),
  musicplayer: () => import('@/apps/MusicPlayer'),
  photoviewer: () => import('@/apps/PhotoViewer'),
  drawing: () => import('@/apps/Drawing'),
  camera: () => import('@/apps/Camera'),
  videoplayer: () => import('@/apps/VideoPlayer'),
  notes: () => import('@/apps/Notes'),
  spreadsheet: () => import('@/apps/Spreadsheet'),
  todo: () => import('@/apps/Todo'),
  pdfviewer: () => import('@/apps/PDFViewer'),
  voicerecorder: () => import('@/apps/VoiceRecorder'),
  reminders: () => import('@/apps/Reminders'),
  codeeditor: () => import('@/apps/CodeEditor'),
  jsonformatter: () => import('@/apps/JSONFormatter'),
  regextester: () => import('@/apps/RegexTester'),
  markdownpreview: () => import('@/apps/MarkdownPreview'),
  htmleditor: () => import('@/apps/HTMLEditor'),
  colorpicker: () => import('@/apps/ColorPicker'),
  passwordgen: () => import('@/apps/PasswordGen'),
  stopwatch: () => import('@/apps/Stopwatch'),
  timer: () => import('@/apps/Timer'),
  weather: () => import('@/apps/Weather'),
  unitconverter: () => import('@/apps/UnitConverter'),
  qrcode: () => import('@/apps/QRCode'),
  translator: () => import('@/apps/Translator'),
  systemmonitor: () => import('@/apps/SystemMonitor'),
  diskusage: () => import('@/apps/DiskUsage'),
  mail: () => import('@/apps/Mail'),
  chat: () => import('@/apps/Chat'),
  contacts: () => import('@/apps/Contacts'),
  news: () => import('@/apps/News'),
  stocks: () => import('@/apps/Stocks'),
  paint: () => import('@/apps/Paint'),
  wiki: () => import('@/apps/Wiki'),
  rssreader: () => import('@/apps/RSSReader'),
  whiteboard: () => import('@/apps/Whiteboard'),
  dictionary: () => import('@/apps/Dictionary'),
  hashgenerator: () => import('@/apps/HashGenerator'),
  diffchecker: () => import('@/apps/DiffChecker'),
  binaryclock: () => import('@/apps/BinaryClock'),
  calculatorpro: () => import('@/apps/CalculatorPro'),
  mathgraph: () => import('@/apps/MathGraph'),
  bmi: () => import('@/apps/BMI'),
  typeracer: () => import('@/apps/games/TypeRacer'),
  connect4: () => import('@/apps/games/Connect4'),
  reversi: () => import('@/apps/games/Reversi'),
  blackjack: () => import('@/apps/games/Blackjack'),
  quiz: () => import('@/apps/games/Quiz'),
  benchmark: () => import('@/apps/Benchmark'),
  network: () => import('@/apps/Network'),
  presentation: () => import('@/apps/Presentation'),
  governance: () => import('@/apps/GovernanceConsole'),
  modelrouter: () => import('@/apps/ModelRouter'),
  execution: () => import('@/apps/ExecutionTimeline'),
  auditlogs: () => import('@/apps/AuditLogs'),
  approvalgates: () => import('@/apps/ApprovalGates'),
};

const loadedComponents: Record<string, React.ComponentType<any>> = {};

function getAppComponent(appId: string): React.ComponentType<any> | null {
  if (loadedComponents[appId]) return loadedComponents[appId];
  const importFn = appImports[appId];
  if (!importFn) return null;
  const LazyComponent = lazy(importFn);
  loadedComponents[appId] = LazyComponent;
  return LazyComponent;
}

export default function AppLoader() {
  const { windows } = useOS();

  return (
    <>
      {windows
        .filter((w) => !w.isMinimized)
        .map((win) => {
          const AppComponent = getAppComponent(win.appId);
          if (!AppComponent) return null;

          return (
            <WindowComponent key={win.id} window={win}>
              <Suspense
                fallback={
                  <div className="w-full h-full flex items-center justify-center bg-[#0d1926]">
                    <div className="flex flex-col items-center gap-3">
                      <div className="w-8 h-8 border-2 border-blue-500/20 border-t-blue-400 rounded-full animate-spin" />
                      <span className="text-xs text-blue-400/50">Loading...</span>
                    </div>
                  </div>
                }
              >
                <AppComponent windowId={win.id} data={win.data} />
              </Suspense>
            </WindowComponent>
          );
        })}
    </>
  );
}
