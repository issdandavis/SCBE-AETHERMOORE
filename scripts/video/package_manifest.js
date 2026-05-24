#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { spawnSync } = require('child_process');

function usage() {
  console.error(
    'Usage: node package_manifest.js --video <mp4> --out <manifest.json> [--srt captions.srt] [--thumbnail image] [--metadata youtube.json] [--quality-report quality-gate.json] [--preset youtube-1080p-story]'
  );
  process.exit(2);
}

const argv = process.argv.slice(2);
const opts = {};
for (let i = 0; i < argv.length; i++) {
  const arg = argv[i];
  if (arg === '--video') opts.video = argv[++i];
  else if (arg === '--srt') opts.srt = argv[++i];
  else if (arg === '--thumbnail') opts.thumbnail = argv[++i];
  else if (arg === '--metadata') opts.metadata = argv[++i];
  else if (arg === '--quality-report') opts.qualityReport = argv[++i];
  else if (arg === '--preset') opts.preset = argv[++i];
  else if (arg === '--out') opts.out = argv[++i];
  else if (arg === '--help') usage();
}
if (!opts.video || !opts.out) usage();

function resolveExisting(label, value) {
  if (!value) return null;
  const resolved = path.resolve(value);
  if (!fs.existsSync(resolved)) throw new Error(`${label} not found: ${resolved}`);
  return resolved;
}

function sha256(filePath) {
  return new Promise((resolve, reject) => {
    const hash = crypto.createHash('sha256');
    const stream = fs.createReadStream(filePath);
    stream.on('error', reject);
    stream.on('data', (chunk) => hash.update(chunk));
    stream.on('end', () => resolve(hash.digest('hex')));
  });
}

async function fileEntry(label, value) {
  const resolved = resolveExisting(label, value);
  if (!resolved) return null;
  const stat = fs.statSync(resolved);
  return {
    path: resolved,
    bytes: stat.size,
    sha256: await sha256(resolved),
    mtime: stat.mtime.toISOString(),
  };
}

function ffprobe(filePath) {
  const result = spawnSync(
    'ffprobe',
    ['-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', filePath],
    {
      encoding: 'utf8',
    }
  );
  if (result.status !== 0) return null;
  return JSON.parse(result.stdout);
}

function readJson(value) {
  if (!value) return null;
  return JSON.parse(fs.readFileSync(path.resolve(value), 'utf8'));
}

(async () => {
  try {
    const video = await fileEntry('video', opts.video);
    const srt = await fileEntry('srt', opts.srt);
    const thumbnail = await fileEntry('thumbnail', opts.thumbnail);
    const metadataEntry = await fileEntry('metadata', opts.metadata);
    const qualityEntry = await fileEntry('quality-report', opts.qualityReport);
    const metadata = readJson(opts.metadata);
    const quality = readJson(opts.qualityReport);
    const probe = ffprobe(video.path);

    const manifest = {
      schema: 'scbe.youtube.video-package.v1',
      created_at: new Date().toISOString(),
      preset: opts.preset || 'youtube-1080p-story',
      assets: {
        video,
        srt,
        thumbnail,
        metadata: metadataEntry,
        qualityReport: qualityEntry,
      },
      youtube: metadata?.youtube || metadata || null,
      quality: quality
        ? {
            ok: Boolean(quality.summary?.ok),
            readinessScore: quality.summary?.readinessScore ?? null,
            storyReady: quality.summary?.storyReady ?? null,
            hardFailures: quality.summary?.hardFailures ?? null,
            warnings: quality.summary?.warnings ?? null,
            storyMode: Boolean(quality.storyMode),
          }
        : null,
      probe,
    };

    const out = path.resolve(opts.out);
    fs.mkdirSync(path.dirname(out), { recursive: true });
    fs.writeFileSync(out, JSON.stringify(manifest, null, 2) + '\n', 'utf8');
    console.log('Wrote video package manifest to', out);
    process.exit(0);
  } catch (err) {
    console.error('package manifest failed:', String(err));
    process.exit(1);
  }
})();
