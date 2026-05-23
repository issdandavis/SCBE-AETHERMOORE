#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { spawn } = require('child_process');

function usage() {
  console.error('Usage: node upload.js --file <path> [--title] [--description] [--privacy] [--receipt-out <path>]');
  process.exit(2);
}

const argv = process.argv.slice(2);
const opts = {};
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === '--file') opts.file = argv[++i];
  else if (a === '--title') opts.title = argv[++i];
  else if (a === '--description') opts.description = argv[++i];
  else if (a === '--privacy') opts.privacy = argv[++i];
  else if (a === '--receipt-out') opts.receiptOut = argv[++i];
  else if (a === '--help') usage();
}
if (!opts.file) usage();
opts.file = path.resolve(opts.file);
if (!fs.existsSync(opts.file)) {
  console.error('file not found:', opts.file);
  process.exit(3);
}

const CLIENT_ID = process.env.YT_CLIENT_ID || process.env.CLIENT_ID;
const CLIENT_SECRET = process.env.YT_CLIENT_SECRET || process.env.CLIENT_SECRET;
const REFRESH_TOKEN = process.env.YT_REFRESH_TOKEN || process.env.REFRESH_TOKEN;
const CHANNEL_ID = process.env.YT_CHANNEL_ID || process.env.CHANNEL_ID;

if (!CLIENT_ID || !CLIENT_SECRET || !REFRESH_TOKEN) {
  console.error('Missing YT_CLIENT_ID, YT_CLIENT_SECRET, or YT_REFRESH_TOKEN in env');
  process.exit(4);
}

async function refreshAccessToken(clientId, clientSecret, refreshToken) {
  const url = 'https://oauth2.googleapis.com/token';
  const body = new URLSearchParams();
  body.set('client_id', clientId);
  body.set('client_secret', clientSecret);
  body.set('refresh_token', refreshToken);
  body.set('grant_type', 'refresh_token');
  const res = await fetch(url, { method: 'POST', body });
  if (!res.ok) throw new Error('token refresh failed: ' + res.status + ' ' + (await res.text()));
  const j = await res.json();
  if (!j.access_token) throw new Error('no access_token returned');
  return j.access_token;
}

async function initiateResumable(metadata, accessToken, fileSize, mimeType) {
  const url = 'https://www.googleapis.com/upload/youtube/v3/videos?part=snippet,status&uploadType=resumable';
  const headers = {
    Authorization: 'Bearer ' + accessToken,
    'Content-Type': 'application/json; charset=UTF-8',
    'X-Upload-Content-Length': String(fileSize),
    'X-Upload-Content-Type': mimeType,
  };
  const res = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify(metadata),
  });
  if (!(res.status >= 200 && res.status < 300)) {
    const txt = await res.text();
    throw new Error('initiate upload failed: ' + res.status + ' ' + txt);
  }
  const uploadUrl = res.headers.get('location');
  if (!uploadUrl) throw new Error('no upload URL returned');
  return uploadUrl;
}

async function uploadWholeFile(uploadUrl, filePath) {
  const stat = fs.statSync(filePath);
  const size = stat.size;
  const stream = fs.createReadStream(filePath);
  // single-chunk PUT with Content-Range
  const headers = {
    'Content-Length': String(size),
    'Content-Range': `bytes 0-${size - 1}/${size}`,
  };
  const res = await fetch(uploadUrl, { method: 'PUT', headers, body: stream });
  if (!(res.status >= 200 && res.status < 300)) {
    const txt = await res.text();
    throw new Error('upload failed: ' + res.status + ' ' + txt);
  }
  // success response contains resource representation
  const j = await res.json();
  return j;
}

async function pollProcessing(videoId, accessToken, maxAttempts = 30) {
  const url = (id) => `https://www.googleapis.com/youtube/v3/videos?part=processingDetails&id=${id}`;
  let attempt = 0;
  while (attempt < maxAttempts) {
    attempt++;
    const res = await fetch(url(videoId), { headers: { Authorization: 'Bearer ' + accessToken } });
    if (!res.ok) {
      await new Promise((r) => setTimeout(r, 1000 * attempt));
      continue;
    }
    const j = await res.json();
    const items = j.items || [];
    if (items.length === 0) {
      await new Promise((r) => setTimeout(r, 1000 * attempt));
      continue;
    }
    const pd = items[0].processingDetails || {};
    const status = pd.processingStatus || 'unknown';
    console.log('processingStatus', status);
    if (status === 'succeeded' || status === 'done' || status === 'processed') return { ok: true, details: pd };
    if (status === 'failed') return { ok: false, details: pd };
    // backoff
    await new Promise((r) => setTimeout(r, Math.min(15000, 2000 * attempt)));
  }
  return { ok: false, details: { reason: 'timeout' } };
}

function computeSha256Stream(filePath) {
  return new Promise((resolve, reject) => {
    const hash = crypto.createHash('sha256');
    const s = fs.createReadStream(filePath);
    s.on('error', reject);
    s.on('data', (chunk) => hash.update(chunk));
    s.on('end', () => resolve(hash.digest('hex')));
  });
}

(async () => {
  try {
    const filePath = opts.file;
    const title = opts.title || path.basename(filePath);
    const description = opts.description || '';
    const privacyStatus = opts.privacy || 'private';
    const mimeType = 'video/mp4';
    const stat = fs.statSync(filePath);
    const fileSize = stat.size;

    console.log('Refreshing access token...');
    const accessToken = await refreshAccessToken(CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN);

    const metadata = {
      snippet: {
        title: title,
        description: description,
        categoryId: '22',
      },
      status: {
        privacyStatus: privacyStatus,
        selfDeclaredMadeForKids: false,
      },
    };

    console.log('Initiating resumable upload...');
    const uploadUrl = await initiateResumable(metadata, accessToken, fileSize, mimeType);
    console.log('Upload URL:', uploadUrl);

    console.log('Uploading file (single PUT)...');
    const resource = await uploadWholeFile(uploadUrl, filePath);
    const videoId = (resource && resource.id) || (resource && resource.videoId) || null;
    console.log('Upload response videoId=', videoId);

    const sha256 = await computeSha256Stream(filePath);

    let processing = null;
    if (videoId) {
      console.log('Polling processing status...');
      processing = await pollProcessing(videoId, accessToken, 40);
    }

    const receipt = {
      file: filePath,
      sha256,
      videoId,
      uploadResponse: resource,
      processing,
      uploaded_at: new Date().toISOString(),
    };

    const out = opts.receiptOut || path.join(process.cwd(), 'youtube-upload-receipt.json');
    fs.writeFileSync(out, JSON.stringify(receipt, null, 2) + '\n', 'utf8');
    console.log('Wrote receipt to', out);
    process.exit(0);
  } catch (err) {
    console.error('upload error:', String(err));
    process.exit(1);
  }
})();
