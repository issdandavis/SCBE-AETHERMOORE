export type AppCapabilityStatus = 'real' | 'local' | 'download-ready';

export interface AppCapability {
  appId: string;
  status: AppCapabilityStatus;
  label: string;
  memoryProfile: 'hot' | 'lazy' | 'deferred';
  proof: string;
  goal: string;
}

const REAL_SURFACE_IDS = new Set(['terminal', 'multiagent', 'browser', 'layeredabacus']);

const DOWNLOAD_READY_IDS = new Set([
  'files',
  'settings',
  'taskmanager',
  'search',
  'codeeditor',
  'musicplayer',
  'photoviewer',
  'camera',
  'videoplayer',
  'voicerecorder',
  'weather',
  'systemmonitor',
  'diskusage',
  'mail',
  'chat',
  'contacts',
  'news',
  'stocks',
  'wiki',
  'rssreader',
  'network',
  'governance',
  'modelrouter',
  'execution',
  'auditlogs',
  'approvalgates',
]);

const REAL_PROOFS: Record<string, string> = {
  browser: 'Bridge /browser/open launches Chromium and /artifact serves the capture.',
  layeredabacus: 'Runtime abacusSetRow/addLayer tests calculate chunked decimal and prime rows.',
  multiagent: 'Bridge /actions, /actions/run, /terminal/run, and /screen/capture receipts.',
  terminal: 'Bridge /terminal/run executes real PowerShell in the repo.',
};

const REAL_GOALS: Record<string, string> = {
  browser: 'Persistent tab sessions with click/type/snapshot actions.',
  layeredabacus: 'Expose reusable worksheet presets for coding, math, and routing tasks.',
  multiagent: 'Route one-button action bundles into governed agent workflows.',
  terminal: 'Keep shell parity with PowerShell while adding SCBE receipts and slash commands.',
};

const DOWNLOAD_READY_GOALS: Record<string, string> = {
  auditlogs: 'Wire to the SCBE receipt ledger and event queue.',
  camera: 'Gate browser camera permissions and save captures through the bridge.',
  chat: 'Wire to configured model providers and local utterance logging.',
  codeeditor: 'Attach to real repo files and pre-push format/lint templates.',
  contacts: 'Import/export contacts through user-approved local files.',
  diskusage: 'Read real disk stats through the bridge instead of static UI values.',
  execution: 'Render real action receipts, queue states, and retry timelines.',
  files: 'Attach to a governed local filesystem bridge.',
  governance: 'Pull live GeoSeal decisions and receipt evidence.',
  mail: 'Connect only through configured, user-approved mail connectors.',
  modelrouter: 'Read actual model inventory, provider health, and benchmark rows.',
  musicplayer: 'Load local media files without bundling heavy assets.',
  network: 'Run real ping/DNS/HTTP checks through the bridge.',
  news: 'Use a configured RSS/news connector with source labels.',
  photoviewer: 'Load local images through the file bridge.',
  rssreader: 'Import feeds and cache items locally.',
  search: 'Index the local app/file/action manifest.',
  settings: 'Persist desktop, bridge, and connector settings.',
  stocks: 'Use a configured market-data provider with timestamps.',
  systemmonitor: 'Read real process and memory stats through the bridge.',
  taskmanager: 'Control real windows/actions and show bridge process state.',
  videoplayer: 'Load local video files without bundling heavy assets.',
  voicerecorder: 'Gate microphone permissions and save audio through the bridge.',
  weather: 'Use a configured weather provider with timestamps.',
  wiki: 'Use the real browser/search bridge for wiki lookup.',
};

export function isLaunchSurface(appId: string): boolean {
  return REAL_SURFACE_IDS.has(appId);
}

export function getAppCapability(appId: string): AppCapability {
  if (REAL_SURFACE_IDS.has(appId)) {
    return {
      appId,
      goal: REAL_GOALS[appId] || 'Keep this surface bridge-backed and test-proven.',
      label: 'real',
      memoryProfile: 'hot',
      proof: REAL_PROOFS[appId] || 'Bridge-backed surface with runtime coverage.',
      status: 'real',
    };
  }

  if (DOWNLOAD_READY_IDS.has(appId)) {
    return {
      appId,
      goal:
        DOWNLOAD_READY_GOALS[appId] ||
        'Wire the shell to a real connector or bridge before launch.',
      label: 'download-ready',
      memoryProfile: 'deferred',
      proof:
        'App shell is lazy-loadable; production function is deferred until connector/backend install.',
      status: 'download-ready',
    };
  }

  return {
    appId,
    goal: 'Keep as a lazy-loaded local utility with a deterministic smoke test before promotion.',
    label: 'local',
    memoryProfile: 'lazy',
    proof:
      'Lazy-loaded local browser app; runtime benchmark can open the surface without extra services.',
    status: 'local',
  };
}

export function summarizeCapabilities(appIds: string[]) {
  const counts = {
    total: appIds.length,
    real: 0,
    local: 0,
    download_ready: 0,
  };

  for (const id of appIds) {
    const status = getAppCapability(id).status;
    if (status === 'real') counts.real += 1;
    if (status === 'local') counts.local += 1;
    if (status === 'download-ready') counts.download_ready += 1;
  }

  return counts;
}
