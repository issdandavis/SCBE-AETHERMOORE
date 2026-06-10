#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

function usage() {
  console.error(
    'Usage: node package.js --out youtube-metadata.json --title <title> [--description-file desc.md] [--description text] [--chapters chapters.json] [--tags "a,b"] [--privacy private|unlisted|public] [--category-id 22]'
  );
  process.exit(2);
}

const argv = process.argv.slice(2);
const opts = { privacy: 'private', categoryId: '22' };
for (let i = 0; i < argv.length; i++) {
  const arg = argv[i];
  if (arg === '--title') opts.title = argv[++i];
  else if (arg === '--description') opts.description = argv[++i];
  else if (arg === '--description-file') opts.descriptionFile = argv[++i];
  else if (arg === '--chapters') opts.chapters = argv[++i];
  else if (arg === '--tags') opts.tags = argv[++i];
  else if (arg === '--privacy') opts.privacy = argv[++i];
  else if (arg === '--category-id') opts.categoryId = argv[++i];
  else if (arg === '--out') opts.out = argv[++i];
  else if (arg === '--help') usage();
}
if (!opts.title || !opts.out) usage();

function readText(filePath) {
  return fs.readFileSync(path.resolve(filePath), 'utf8').trim();
}

function parseTime(value) {
  const parts = String(value).split(':').map(Number);
  if (parts.some((part) => !Number.isFinite(part))) return null;
  return parts.reduce((acc, part) => acc * 60 + part, 0);
}

function formatTime(seconds) {
  const sec = Math.max(0, Math.floor(Number(seconds) || 0));
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  if (h) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  return `${m}:${String(s).padStart(2, '0')}`;
}

function loadChapters(value) {
  if (!value) return [];
  const raw = JSON.parse(readText(value));
  if (!Array.isArray(raw)) throw new Error('--chapters must be a JSON array');
  return raw.map((item) => ({
    timestamp: item.timestamp || formatTime(item.start ?? item.seconds ?? 0),
    title: String(item.title || item.name || '').trim(),
  }));
}

function validateChapters(chapters) {
  const errors = [];
  if (!chapters.length) return errors;
  if (parseTime(chapters[0].timestamp) !== 0) errors.push('first chapter must start at 0:00');
  let previous = -1;
  for (const chapter of chapters) {
    const seconds = parseTime(chapter.timestamp);
    if (seconds === null) errors.push(`invalid chapter timestamp: ${chapter.timestamp}`);
    if (!chapter.title) errors.push(`chapter at ${chapter.timestamp} has no title`);
    if (seconds !== null && seconds <= previous)
      errors.push(`chapter timestamps must be increasing at ${chapter.timestamp}`);
    previous = seconds ?? previous;
  }
  if (chapters.length > 0 && chapters.length < 3)
    errors.push('YouTube chapters need at least 3 timestamps to render as chapters');
  return errors;
}

try {
  const baseDescription = opts.descriptionFile
    ? readText(opts.descriptionFile)
    : opts.description || '';
  const chapters = loadChapters(opts.chapters);
  const chapterErrors = validateChapters(chapters);
  if (chapterErrors.length) throw new Error(chapterErrors.join('; '));
  const chapterBlock = chapters.length
    ? '\n\nChapters:\n' +
      chapters.map((chapter) => `${chapter.timestamp} ${chapter.title}`).join('\n')
    : '';
  const description = `${baseDescription}${chapterBlock}`.trim();
  if (opts.title.length > 100) throw new Error('YouTube title exceeds 100 characters');
  if (description.length > 5000) throw new Error('YouTube description exceeds 5000 characters');
  const tags = opts.tags
    ? opts.tags
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean)
    : [];
  const metadata = {
    youtube: {
      title: opts.title,
      description,
      privacy: opts.privacy,
      categoryId: opts.categoryId,
      tags,
      chapters,
      selfDeclaredMadeForKids: false,
    },
    created_at: new Date().toISOString(),
  };
  const out = path.resolve(opts.out);
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, JSON.stringify(metadata, null, 2) + '\n', 'utf8');
  console.log('Wrote YouTube metadata package to', out);
  process.exit(0);
} catch (err) {
  console.error('youtube package failed:', String(err));
  process.exit(1);
}
