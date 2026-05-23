#!/usr/bin/env node
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

function usage() {
  console.error('Usage: node verify.js --file <path> [--out <path>]');
  process.exit(2);
}

const argv = process.argv.slice(2);
let file = null;
let out = null;
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === '--file') file = argv[++i];
  else if (a === '--out') out = argv[++i];
  else if (a === '--help') usage();
}
if (!file) usage();
file = path.resolve(file);
if (!fs.existsSync(file)) {
  console.error('File not found:', file);
  process.exit(3);
}

function runFfprobe(filePath) {
  return new Promise((resolve, reject) => {
    const args = ['-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', filePath];
    const p = spawn('ffprobe', args);
    let out = '';
    let err = '';
    p.stdout.on('data', (c) => (out += c.toString()));
    p.stderr.on('data', (c) => (err += c.toString()));
    p.on('close', (code) => {
      if (code !== 0) return reject(new Error('ffprobe failed: ' + err));
      try {
        const parsed = JSON.parse(out);
        resolve(parsed);
      } catch (e) {
        reject(e);
      }
    });
  });
}

function computeSha256(filePath) {
  return new Promise((resolve, reject) => {
    const crypto = require('crypto');
    const hash = crypto.createHash('sha256');
    const s = fs.createReadStream(filePath);
    s.on('error', reject);
    s.on('data', (d) => hash.update(d));
    s.on('end', () => resolve(hash.digest('hex')));
  });
}

(async () => {
  try {
    const info = await runFfprobe(file);
    const sha256 = await computeSha256(file);

    // Basic checks
    const streams = info.streams || [];
    const hasVideo = streams.some((s) => s.codec_type === 'video');
    const hasAudio = streams.some((s) => s.codec_type === 'audio');

    const videoStream = streams.find((s) => s.codec_type === 'video');
    const audioStream = streams.find((s) => s.codec_type === 'audio');

    const checks = [];
    if (!hasVideo) checks.push({ ok: false, reason: 'no_video_stream' });
    if (!hasAudio) checks.push({ ok: false, reason: 'no_audio_stream' });

    if (videoStream) {
      const codec = (videoStream.codec_name || '').toLowerCase();
      if (!(codec === 'h264' || codec === 'vp9' || codec === 'hevc')) {
        checks.push({ ok: false, reason: 'video_codec_not_recommended', codec });
      }
      if (videoStream.width && videoStream.height) {
        checks.push({ ok: true, reason: 'resolution', w: videoStream.width, h: videoStream.height });
      }
    }
    if (audioStream) {
      const acodec = (audioStream.codec_name || '').toLowerCase();
      if (!(acodec === 'aac' || acodec === 'opus')) {
        checks.push({ ok: false, reason: 'audio_codec_not_recommended', codec: acodec });
      }
    }

    const result = {
      file: file,
      sha256: sha256,
      format: info.format || null,
      streams: streams,
      checks: checks,
      verified_at: new Date().toISOString(),
    };

    const outJson = JSON.stringify(result, null, 2) + '\n';
    if (out) {
      fs.writeFileSync(out, outJson, 'utf8');
      console.log('Wrote verify receipt to', out);
    } else {
      console.log(outJson);
    }

    // Exit code: 0 if no negative checks, 1 otherwise
    const negative = checks.some((c) => c.ok === false);
    process.exit(negative ? 1 : 0);
  } catch (err) {
    console.error('verify failed:', String(err));
    process.exit(2);
  }
})();
