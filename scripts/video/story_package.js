#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

function usage() {
  console.error(
    'Usage: node story_package.js --video <mp4> --title <title> --out-dir <dir> [--description-file desc.md] [--description text] [--chapters chapters.json] [--srt captions.srt] [--thumbnail image] [--source-text manuscript.md] [--tags "a,b"] [--privacy private|unlisted|public]'
  );
  process.exit(2);
}

const argv = process.argv.slice(2);
const opts = { privacy: 'private' };
for (let i = 0; i < argv.length; i++) {
  const arg = argv[i];
  if (arg === '--video') opts.video = argv[++i];
  else if (arg === '--title') opts.title = argv[++i];
  else if (arg === '--description') opts.description = argv[++i];
  else if (arg === '--description-file') opts.descriptionFile = argv[++i];
  else if (arg === '--chapters') opts.chapters = argv[++i];
  else if (arg === '--srt') opts.srt = argv[++i];
  else if (arg === '--thumbnail') opts.thumbnail = argv[++i];
  else if (arg === '--source-text') opts.sourceText = argv[++i];
  else if (arg === '--tags') opts.tags = argv[++i];
  else if (arg === '--privacy') opts.privacy = argv[++i];
  else if (arg === '--out-dir') opts.outDir = argv[++i];
  else if (arg === '--help') usage();
}
if (!opts.video || !opts.title || !opts.outDir) usage();

function repoPath(...parts) {
  return path.resolve(__dirname, '..', '..', ...parts);
}

function requireExisting(label, value) {
  if (!value) return null;
  const resolved = path.resolve(value);
  if (!fs.existsSync(resolved)) throw new Error(`${label} not found: ${resolved}`);
  return resolved;
}

function runStep(name, args) {
  console.log(`\n== ${name} ==`);
  const result = spawnSync(process.execPath, args, {
    cwd: repoPath(),
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  if (result.status !== 0) {
    throw new Error(`${name} failed with exit ${result.status}`);
  }
}

try {
  const video = requireExisting('video', opts.video);
  const srt = requireExisting('srt', opts.srt);
  const thumbnail = requireExisting('thumbnail', opts.thumbnail);
  const sourceText = requireExisting('source-text', opts.sourceText);
  const chapters = requireExisting('chapters', opts.chapters);
  const descriptionFile = requireExisting('description-file', opts.descriptionFile);
  const outDir = path.resolve(opts.outDir);
  fs.mkdirSync(outDir, { recursive: true });

  const metadata = path.join(outDir, 'youtube-metadata.json');
  const quality = path.join(outDir, 'quality-gate.json');
  const manifest = path.join(outDir, 'video-package.json');

  const packageArgs = [
    repoPath('scripts', 'youtube', 'package.js'),
    '--out',
    metadata,
    '--title',
    opts.title,
    '--privacy',
    opts.privacy,
  ];
  if (opts.descriptionFile) packageArgs.push('--description-file', descriptionFile);
  if (opts.description) packageArgs.push('--description', opts.description);
  if (chapters) packageArgs.push('--chapters', chapters);
  if (opts.tags) packageArgs.push('--tags', opts.tags);
  runStep('Build YouTube metadata', packageArgs);

  const qualityArgs = [
    repoPath('scripts', 'video', 'quality_gate.js'),
    '--file',
    video,
    '--metadata',
    metadata,
    '--out',
    quality,
    '--story',
  ];
  if (srt) qualityArgs.push('--srt', srt);
  if (thumbnail) qualityArgs.push('--thumbnail', thumbnail);
  if (sourceText) qualityArgs.push('--source-text', sourceText);
  runStep('Run story quality gate', qualityArgs);

  const manifestArgs = [
    repoPath('scripts', 'video', 'package_manifest.js'),
    '--video',
    video,
    '--metadata',
    metadata,
    '--quality-report',
    quality,
    '--out',
    manifest,
    '--preset',
    'youtube-1080p-story',
  ];
  if (srt) manifestArgs.push('--srt', srt);
  if (thumbnail) manifestArgs.push('--thumbnail', thumbnail);
  runStep('Build video package manifest', manifestArgs);

  const qualityPayload = JSON.parse(fs.readFileSync(quality, 'utf8'));
  console.log(
    JSON.stringify(
      {
        schema: 'scbe.video.story_package.result.v1',
        ok: Boolean(qualityPayload.summary?.ok),
        storyReady: Boolean(qualityPayload.summary?.storyReady),
        readinessScore: qualityPayload.summary?.readinessScore ?? null,
        manifest,
        quality,
        metadata,
      },
      null,
      2
    )
  );
} catch (err) {
  console.error('story package failed:', String(err));
  process.exit(1);
}
