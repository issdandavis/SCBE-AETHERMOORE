'use strict';

const fs = require('node:fs');
const path = require('node:path');

const DOCS_ROOT = path.join(process.cwd(), 'docs');

const MIME_TYPES = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.md': 'text/markdown; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.txt': 'text/plain; charset=utf-8',
  '.xml': 'application/xml; charset=utf-8',
};

function docsPath(relativePath) {
  const normalized = path.normalize(relativePath || '').replace(/^(\.\.(\/|\\|$))+/, '');
  const filePath = path.join(DOCS_ROOT, normalized);
  if (!filePath.startsWith(`${DOCS_ROOT}${path.sep}`) && filePath !== DOCS_ROOT) {
    throw new Error('invalid docs path');
  }
  return filePath;
}

function sendFile(req, res, filePath, unavailableError) {
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    res.setHeader('Allow', 'GET, HEAD');
    return res.status(405).json({ ok: false, error: 'method_not_allowed' });
  }

  try {
    const body = fs.readFileSync(filePath);
    const ext = path.extname(filePath).toLowerCase();
    res.setHeader('Content-Type', MIME_TYPES[ext] || 'application/octet-stream');
    res.setHeader('Cache-Control', 'public, max-age=300, s-maxage=300');
    return res.status(200).send(req.method === 'HEAD' ? '' : body);
  } catch (err) {
    return res.status(404).json({
      ok: false,
      error: unavailableError,
      detail: err && err.message ? err.message : String(err),
    });
  }
}

function serveDocsHtml(req, res, fileName, unavailableError) {
  return sendFile(req, res, docsPath(fileName), unavailableError);
}

function serveDocsAsset(req, res) {
  const rawPath = Array.isArray(req.query && req.query.path)
    ? req.query.path[0]
    : req.query && req.query.path;
  const assetPath = String(rawPath || '');
  if (!assetPath || assetPath.includes('\0')) {
    return res.status(400).json({ ok: false, error: 'asset_path_required' });
  }
  return sendFile(req, res, docsPath(path.join('static', assetPath)), 'static_asset_unavailable');
}

module.exports = {
  serveDocsAsset,
  serveDocsHtml,
};
