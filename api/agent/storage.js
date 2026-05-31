'use strict';

const { readJsonBody, sendJson, setCors } = require('../_agent_common');

const MAX_EXPORT_BYTES = 256 * 1024;

const WORKSPACE_FORMATION = {
  schema_version: 'aethermoor.bus.workspace_formation.v1',
  default_root: '.aethermoor-bus/workspaces',
  lifecycle: 'temp-local-first-offload-required',
  folders: [
    {
      path: '00_inbox',
      role: 'raw drops, user uploads, unclassified imports',
      ship: false,
    },
    {
      path: '10_work',
      role: 'active editable working files',
      ship: false,
    },
    {
      path: '20_receipts',
      role: 'governance verdicts, hashes, signatures, run receipts',
      ship: true,
    },
    {
      path: '30_exports',
      role: 'customer-ready packets and handoff bundles',
      ship: true,
    },
    {
      path: '40_refs',
      role: 'non-secret reference files and source notes',
      ship: true,
    },
    {
      path: '90_tmp',
      role: 'scratch files; delete after successful offload',
      ship: false,
    },
  ],
  transport_stops: ['local_download', 'browser_local', 'github', 'dropbox', 'onedrive', 'gdrive'],
  rules: [
    'Classify before offload.',
    'Never export secrets by default.',
    'Receipts and manifests travel with customer work.',
    'Temporary local workspaces are disposable after offload verification.',
    'External storage is user-designated; the bus does not retain export content.',
  ],
};

const PROVIDERS = [
  {
    id: 'local_download',
    label: 'Download to this device',
    cost: 'zero',
    auth: 'none',
    mode: 'browser_download',
    available: true,
    recommended: true,
    description: 'Create a JSON export packet and let the browser save it locally.',
  },
  {
    id: 'browser_local',
    label: 'Browser local storage',
    cost: 'zero',
    auth: 'none',
    mode: 'local_storage',
    available: true,
    recommended: true,
    description: 'Keep small conversation and preference records on the device.',
  },
  {
    id: 'github',
    label: 'GitHub',
    cost: 'user_account',
    auth: 'user_or_server_token',
    mode: 'external_handoff',
    available: true,
    description:
      'Export packet can be committed, attached to an issue, or uploaded through a user-authorized GitHub flow.',
  },
  {
    id: 'dropbox',
    label: 'Dropbox',
    cost: 'user_account',
    auth: 'user_oauth',
    mode: 'external_handoff',
    available: true,
    description: 'Export packet can be saved through Dropbox OAuth or manual upload.',
  },
  {
    id: 'onedrive',
    label: 'OneDrive',
    cost: 'user_account',
    auth: 'user_oauth',
    mode: 'external_handoff',
    available: true,
    description:
      'Export packet can be saved through Microsoft OAuth, local sync folder, or manual upload.',
  },
  {
    id: 'gdrive',
    label: 'Google Drive',
    cost: 'user_account',
    auth: 'user_oauth',
    mode: 'external_handoff',
    available: true,
    description:
      'Export packet can be saved through Google OAuth, local Drive mount, or manual upload.',
  },
];

function slugify(value) {
  return (
    String(value || 'scbe-export')
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9._-]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 80) || 'scbe-export'
  );
}

function normalizeContent(value) {
  if (typeof value === 'string') return value;
  return JSON.stringify(value == null ? {} : value, null, 2);
}

function buildExportPacket(body) {
  const content = normalizeContent(body.content || body.payload || {});
  const bytes = Buffer.byteLength(content, 'utf8');
  if (bytes > MAX_EXPORT_BYTES) {
    const error = new Error(`export exceeds ${MAX_EXPORT_BYTES} bytes`);
    error.status = 413;
    throw error;
  }
  const kind = slugify(body.kind || 'agent-bus');
  const name = slugify(body.name || `${kind}-${new Date().toISOString().slice(0, 10)}`);
  const filename = `${name}.json`;
  const packet = {
    schema_version: 'aethermoor.agent.storage_export.v1',
    created_at: new Date().toISOString(),
    kind,
    name,
    filename,
    content_type: 'application/json',
    byte_length: bytes,
    destination_hint: body.destination || 'local_download',
    metadata: body.metadata && typeof body.metadata === 'object' ? body.metadata : {},
    workspace_formation: WORKSPACE_FORMATION,
    content,
  };
  return {
    ok: true,
    cost: 'zero-server-storage',
    storage_policy: 'server does not retain export content',
    provider_options: PROVIDERS,
    packet,
    download: {
      filename,
      mime: 'application/json',
      base64: Buffer.from(JSON.stringify(packet, null, 2), 'utf8').toString('base64'),
    },
  };
}

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(204).end();

  if (req.method === 'GET') {
    return sendJson(res, 200, {
      ok: true,
      cost: 'zero-server-storage',
      default_provider: 'local_download',
      providers: PROVIDERS,
      workspace_formation: WORKSPACE_FORMATION,
    });
  }

  if (req.method !== 'POST') return sendJson(res, 405, { ok: false, error: 'GET or POST only' });

  let body;
  try {
    body = await readJsonBody(req);
    return sendJson(res, 200, buildExportPacket(body || {}));
  } catch (error) {
    return sendJson(res, error.status || 400, {
      ok: false,
      error: String(error.message || error),
    });
  }
};

module.exports._private = {
  buildExportPacket,
  normalizeContent,
  PROVIDERS,
  WORKSPACE_FORMATION,
  slugify,
};
