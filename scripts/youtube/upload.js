#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { spawn } = require('child_process');

function usage() {
  console.error(
    'Usage: node upload.js --file <path> [--title] [--description] [--privacy] [--receipt-out <path>] [--chunk-size-mb 8] [--max-retries 5]\n' +
      '       node upload.js --manifest <video-package.json> [--receipt-out <path>] [--chunk-size-mb 8] [--max-retries 5]'
  );
  process.exit(2);
}

const argv = process.argv.slice(2);
const opts = {};
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === '--manifest') opts.manifest = argv[++i];
  else if (a === '--file') opts.file = argv[++i];
  else if (a === '--title') opts.title = argv[++i];
  else if (a === '--description') opts.description = argv[++i];
  else if (a === '--privacy') opts.privacy = argv[++i];
  else if (a === '--tags')
    opts.tags = argv[++i]
      .split(',')
      .map((tag) => tag.trim())
      .filter(Boolean);
  else if (a === '--category-id') opts.categoryId = argv[++i];
  else if (a === '--made-for-kids') opts.selfDeclaredMadeForKids = true;
  else if (a === '--receipt-out') opts.receiptOut = argv[++i];
  else if (a === '--chunk-size-mb') opts.chunkSizeMb = Number(argv[++i]);
  else if (a === '--max-retries') opts.maxRetries = Number(argv[++i]);
  else if (a === '--help') usage();
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(path.resolve(filePath), 'utf8'));
}

if (opts.manifest) {
  opts.manifest = path.resolve(opts.manifest);
  if (!fs.existsSync(opts.manifest)) {
    console.error('manifest not found:', opts.manifest);
    process.exit(3);
  }
  const manifest = readJson(opts.manifest);
  if (manifest.quality && manifest.quality.ok === false) {
    console.error('manifest quality gate failed; refusing upload:', opts.manifest);
    process.exit(5);
  }
  if (manifest.quality && manifest.quality.storyReady === false) {
    console.error('manifest story readiness gate failed; refusing upload:', opts.manifest);
    process.exit(5);
  }
  const youtube = manifest.youtube || {};
  opts.file = opts.file || manifest.assets?.video?.path;
  opts.title = opts.title || youtube.title;
  opts.description = opts.description || youtube.description;
  opts.privacy = opts.privacy || youtube.privacy || youtube.privacyStatus;
  opts.categoryId = opts.categoryId || youtube.categoryId;
  opts.tags = opts.tags || youtube.tags;
  opts.selfDeclaredMadeForKids =
    typeof opts.selfDeclaredMadeForKids === 'boolean'
      ? opts.selfDeclaredMadeForKids
      : Boolean(youtube.selfDeclaredMadeForKids);
  opts.loadedManifest = manifest;
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
  const url =
    'https://www.googleapis.com/upload/youtube/v3/videos?part=snippet,status&uploadType=resumable';
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

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function parseUploadedOffset(rangeHeader) {
  // YouTube returns Range like "bytes=0-8388607" for committed bytes.
  if (!rangeHeader) return 0;
  const match = String(rangeHeader).match(/bytes=0-(\d+)/i);
  if (!match) return 0;
  return Number(match[1]) + 1;
}

async function queryUploadOffset(uploadUrl, totalSize) {
  const res = await fetch(uploadUrl, {
    method: 'PUT',
    redirect: 'manual',
    headers: {
      'Content-Length': '0',
      'Content-Range': `bytes */${totalSize}`,
    },
  });
  if (res.status === 308) {
    return parseUploadedOffset(res.headers.get('range'));
  }
  if (res.status >= 200 && res.status < 300) {
    const body = await res.text();
    return { complete: true, resource: body ? JSON.parse(body) : {} };
  }
  const txt = await res.text();
  throw new Error('upload offset query failed: ' + res.status + ' ' + txt);
}

async function uploadChunk(uploadUrl, filePath, start, end, totalSize) {
  const stream = fs.createReadStream(filePath, { start, end });
  const headers = {
    'Content-Length': String(end - start + 1),
    'Content-Range': `bytes ${start}-${end}/${totalSize}`,
  };
  return fetch(uploadUrl, {
    method: 'PUT',
    headers,
    body: stream,
    duplex: 'half',
    redirect: 'manual',
  });
}

async function uploadFileResumable(uploadUrl, filePath, chunkSize, maxRetries) {
  const totalSize = fs.statSync(filePath).size;
  let offset = 0;
  while (offset < totalSize) {
    const end = Math.min(offset + chunkSize - 1, totalSize - 1);
    let attempt = 0;
    while (true) {
      try {
        console.log(`Uploading bytes ${offset}-${end}/${totalSize}`);
        const res = await uploadChunk(uploadUrl, filePath, offset, end, totalSize);
        if (res.status === 308) {
          const nextOffset = parseUploadedOffset(res.headers.get('range'));
          offset = Math.max(nextOffset, end + 1);
          break;
        }
        if (res.status >= 200 && res.status < 300) {
          const body = await res.text();
          return body ? JSON.parse(body) : {};
        }
        if (res.status >= 500 || res.status === 429) {
          throw new Error('retryable upload response: ' + res.status + ' ' + (await res.text()));
        }
        throw new Error('upload failed: ' + res.status + ' ' + (await res.text()));
      } catch (err) {
        attempt++;
        if (attempt > maxRetries) throw err;
        const delay = Math.min(30000, 1000 * 2 ** (attempt - 1));
        console.warn(
          `Chunk upload attempt ${attempt} failed: ${String(err)}. Retrying in ${delay}ms...`
        );
        await sleep(delay);
        const status = await queryUploadOffset(uploadUrl, totalSize);
        if (status && status.complete) return status.resource;
        offset = typeof status === 'number' ? status : offset;
        break;
      }
    }
  }
  const status = await queryUploadOffset(uploadUrl, totalSize);
  if (status && status.complete) return status.resource;
  throw new Error('upload ended without final video resource');
}

async function pollProcessing(videoId, accessToken, maxAttempts = 30) {
  const url = (id) =>
    `https://www.googleapis.com/youtube/v3/videos?part=processingDetails&id=${id}`;
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
    if (status === 'succeeded' || status === 'done' || status === 'processed')
      return { ok: true, details: pd };
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
    const chunkSizeMb = opts.chunkSizeMb || Number(process.env.YT_CHUNK_SIZE_MB || 8);
    const maxRetries = opts.maxRetries || Number(process.env.YT_UPLOAD_MAX_RETRIES || 5);
    const chunkSize = Math.max(1, Math.floor(chunkSizeMb)) * 1024 * 1024;
    if (!Number.isFinite(chunkSizeMb) || chunkSizeMb <= 0)
      throw new Error('invalid --chunk-size-mb');
    if (!Number.isFinite(maxRetries) || maxRetries < 0) throw new Error('invalid --max-retries');

    console.log('Refreshing access token...');
    const accessToken = await refreshAccessToken(CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN);

    const metadata = {
      snippet: {
        title: title,
        description: description,
        categoryId: opts.categoryId || '22',
        ...(Array.isArray(opts.tags) && opts.tags.length ? { tags: opts.tags } : {}),
      },
      status: {
        privacyStatus: privacyStatus,
        selfDeclaredMadeForKids: Boolean(opts.selfDeclaredMadeForKids),
      },
    };

    console.log('Initiating resumable upload...');
    const uploadUrl = await initiateResumable(metadata, accessToken, fileSize, mimeType);
    console.log('Upload URL:', uploadUrl);

    console.log(`Uploading file in ${chunkSizeMb} MiB chunks...`);
    const resource = await uploadFileResumable(uploadUrl, filePath, chunkSize, maxRetries);
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
      chunkSize,
      maxRetries,
      manifest: opts.manifest || null,
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
