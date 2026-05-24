#!/usr/bin/env node
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

function usage() {
  console.error(
    'Usage: node quality_gate.js --file <video.mp4> [--srt captions.srt] [--thumbnail image] [--metadata metadata.json] [--source-text manuscript.md] [--out quality-gate.json] [--strict] [--story]'
  );
  process.exit(2);
}

const argv = process.argv.slice(2);
const opts = { strict: false, story: false };
for (let i = 0; i < argv.length; i++) {
  const arg = argv[i];
  if (arg === '--file') opts.file = argv[++i];
  else if (arg === '--srt') opts.srt = argv[++i];
  else if (arg === '--thumbnail') opts.thumbnail = argv[++i];
  else if (arg === '--metadata') opts.metadata = argv[++i];
  else if (arg === '--source-text') opts.sourceText = argv[++i];
  else if (arg === '--out') opts.out = argv[++i];
  else if (arg === '--strict') opts.strict = true;
  else if (arg === '--story') opts.story = true;
  else if (arg === '--help') usage();
}
if (!opts.file) usage();

function resolveExisting(label, value) {
  if (!value) return null;
  const resolved = path.resolve(value);
  if (!fs.existsSync(resolved)) throw new Error(`${label} not found: ${resolved}`);
  return resolved;
}

const file = resolveExisting('file', opts.file);
const srt = resolveExisting('srt', opts.srt);
const thumbnail = resolveExisting('thumbnail', opts.thumbnail);
const metadataPath = resolveExisting('metadata', opts.metadata);
const sourceText = resolveExisting('source-text', opts.sourceText);

function run(command, args) {
  return new Promise((resolve) => {
    const child = spawn(command, args);
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => (stdout += chunk.toString()));
    child.stderr.on('data', (chunk) => (stderr += chunk.toString()));
    child.on('close', (code) => resolve({ code, stdout, stderr }));
  });
}

async function ffprobe(filePath) {
  const result = await run('ffprobe', [
    '-v',
    'quiet',
    '-print_format',
    'json',
    '-show_format',
    '-show_streams',
    filePath,
  ]);
  if (result.code !== 0) throw new Error(`ffprobe failed: ${result.stderr}`);
  return JSON.parse(result.stdout);
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

function streamDuration(stream) {
  return Number(stream && (stream.duration || stream.tags?.DURATION_SECONDS || 0)) || 0;
}

function parseFfmpegIntervals(stderr, kind) {
  const starts = [];
  const intervals = [];
  const startRe = new RegExp(`${kind}_start:\\s*([0-9.]+)`, 'g');
  const endRe = new RegExp(
    `${kind}_end:\\s*([0-9.]+)\\s*\\|\\s*${kind}_duration:\\s*([0-9.]+)`,
    'g'
  );
  let match;
  while ((match = startRe.exec(stderr))) starts.push(Number(match[1]));
  let idx = 0;
  while ((match = endRe.exec(stderr))) {
    intervals.push({
      start: starts[idx++] ?? null,
      end: Number(match[1]),
      duration: Number(match[2]),
    });
  }
  return intervals;
}

async function runFilter(filter) {
  const result = await run('ffmpeg', [
    '-hide_banner',
    '-nostdin',
    '-i',
    file,
    '-vf',
    filter,
    '-an',
    '-f',
    'null',
    '-',
  ]);
  return result.stderr;
}

async function runAudioFilter(filter) {
  const result = await run('ffmpeg', [
    '-hide_banner',
    '-nostdin',
    '-i',
    file,
    '-vn',
    '-af',
    filter,
    '-f',
    'null',
    '-',
  ]);
  return result.stderr;
}

function inspectMoovPlacement(filePath) {
  const stat = fs.statSync(filePath);
  const chunkSize = Math.min(stat.size, 4 * 1024 * 1024);
  const fd = fs.openSync(filePath, 'r');
  try {
    const buffer = Buffer.alloc(chunkSize);
    fs.readSync(fd, buffer, 0, chunkSize, 0);
    const text = buffer.toString('latin1');
    const moov = text.indexOf('moov');
    const mdat = text.indexOf('mdat');
    return {
      checkedBytes: chunkSize,
      moovOffset: moov >= 0 ? moov : null,
      mdatOffset: mdat >= 0 ? mdat : null,
      faststartLikely: moov >= 0 && (mdat < 0 || moov < mdat),
    };
  } finally {
    fs.closeSync(fd);
  }
}

function parseSrtTime(value) {
  const match = value.match(/^(\d+):(\d+):(\d+),(\d+)$/);
  if (!match) return null;
  return (
    Number(match[1]) * 3600 + Number(match[2]) * 60 + Number(match[3]) + Number(match[4]) / 1000
  );
}

function parseSrt(filePath) {
  if (!filePath) return null;
  const text = fs.readFileSync(filePath, 'utf8').replace(/\r\n/g, '\n');
  const cues = [];
  const re = /(\d+)\n(\d+:\d+:\d+,\d+)\s+-->\s+(\d+:\d+:\d+,\d+)\n([\s\S]*?)(?=\n\n|\n*$)/g;
  let match;
  while ((match = re.exec(text))) {
    cues.push({
      index: Number(match[1]),
      start: parseSrtTime(match[2]),
      end: parseSrtTime(match[3]),
      text: match[4].trim(),
    });
  }
  return { file: filePath, cues, first: cues[0] || null, last: cues[cues.length - 1] || null };
}

function validateSrtContinuity(cues) {
  const issues = [];
  let previousEnd = -1;
  for (const cue of cues) {
    if (cue.start === null || cue.end === null || cue.end <= cue.start) {
      issues.push({ cue: cue.index, reason: 'invalid_cue_time', start: cue.start, end: cue.end });
    }
    if (cue.start !== null && cue.start < previousEnd - 0.05) {
      issues.push({ cue: cue.index, reason: 'overlapping_cue', start: cue.start, previousEnd });
    }
    previousEnd = Math.max(previousEnd, cue.end ?? previousEnd);
  }
  return issues;
}

function normalizeWords(text) {
  return (
    String(text || '')
      .toLowerCase()
      .replace(/[`*_~#>\[\]()[\]{}]/g, ' ')
      .match(/[a-z0-9']+/g) || []
  );
}

function finalSourceWordsPresent(sourcePath, cues) {
  if (!sourcePath || !cues.length) return null;
  const sourceWords = normalizeWords(fs.readFileSync(sourcePath, 'utf8'));
  if (!sourceWords.length) return null;
  const needle = sourceWords.slice(-10).join(' ');
  const haystack = normalizeWords(
    cues
      .slice(-8)
      .map((cue) => cue.text)
      .join(' ')
  ).join(' ');
  return {
    finalWords: needle,
    finalCaptionWindow: haystack,
    found: Boolean(needle && haystack.includes(needle)),
  };
}

function parseMetadata(filePath) {
  if (!filePath) return null;
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function metadataYoutube(metadata) {
  if (!metadata) return null;
  return metadata.youtube || metadata;
}

function collectChapters(metadata) {
  if (!metadata) return [];
  if (Array.isArray(metadata.chapters)) return metadata.chapters;
  if (Array.isArray(metadata.youtube?.chapters)) return metadata.youtube.chapters;
  const description = metadata.description || metadata.youtube?.description || '';
  return [...description.matchAll(/(?:^|\n)\s*((?:\d+:)?\d{1,2}:\d{2})\s+(.+)/g)].map((m) => ({
    timestamp: m[1],
    title: m[2].trim(),
  }));
}

function chapterTimeSeconds(value) {
  const parts = value.split(':').map(Number);
  if (parts.some((part) => !Number.isFinite(part))) return null;
  return parts.reduce((acc, part) => acc * 60 + part, 0);
}

function addCheck(checks, severity, ok, reason, details = {}) {
  checks.push({ ok, severity, reason, ...details });
}

function parseVolumeDetect(stderr) {
  const mean = stderr.match(/mean_volume:\s*(-?[0-9.]+)\s*dB/);
  const max = stderr.match(/max_volume:\s*(-?[0-9.]+)\s*dB/);
  return {
    meanVolumeDb: mean ? Number(mean[1]) : null,
    maxVolumeDb: max ? Number(max[1]) : null,
  };
}

function parseIntegratedLufs(stderr) {
  const matches = [...stderr.matchAll(/\bI:\s*(-?[0-9.]+)\s*LUFS/g)];
  if (!matches.length) return null;
  return Number(matches[matches.length - 1][1]);
}

function hasYoutubeCta(text) {
  return /\b(subscribe|notification bell|ring the bell|like|comment|share|next chapter|next episode)\b/i.test(
    text || ''
  );
}

function readinessScore(checks) {
  let score = 100;
  for (const check of checks) {
    if (check.ok) continue;
    score -= check.severity === 'hard' ? 18 : 5;
  }
  return Math.max(0, score);
}

(async () => {
  try {
    const probe = await ffprobe(file);
    const fileHash = await sha256(file);
    const streams = probe.streams || [];
    const video = streams.find((stream) => stream.codec_type === 'video');
    const audio = streams.find((stream) => stream.codec_type === 'audio');
    const formatDuration = Number(probe.format?.duration || 0);
    const videoDuration = streamDuration(video) || formatDuration;
    const audioDuration = streamDuration(audio) || formatDuration;
    const checks = [];

    addCheck(checks, 'hard', Boolean(video), 'has_video_stream');
    addCheck(checks, 'hard', Boolean(audio), 'has_audio_stream');

    if (video) {
      const codec = String(video.codec_name || '').toLowerCase();
      addCheck(
        checks,
        'hard',
        ['h264', 'vp9', 'hevc', 'av1'].includes(codec),
        'video_codec_supported',
        { codec }
      );
      addCheck(
        checks,
        'warn',
        video.width >= 1280 && video.height >= 720,
        'resolution_at_least_720p',
        {
          width: video.width,
          height: video.height,
        }
      );
      if (video.pix_fmt) {
        addCheck(
          checks,
          'warn',
          ['yuv420p', 'yuvj420p'].includes(video.pix_fmt),
          'pixel_format_yuv420p_preferred',
          {
            pix_fmt: video.pix_fmt,
          }
        );
      }
    }
    if (audio) {
      const codec = String(audio.codec_name || '').toLowerCase();
      addCheck(checks, 'hard', ['aac', 'opus'].includes(codec), 'audio_codec_supported', { codec });
      addCheck(checks, 'warn', Number(audio.sample_rate || 0) >= 24000, 'audio_sample_rate_sane', {
        sample_rate: audio.sample_rate,
      });
    }

    addCheck(
      checks,
      'hard',
      Math.abs(videoDuration - audioDuration) <= 3,
      'audio_video_duration_match',
      {
        videoDuration,
        audioDuration,
        delta: Math.abs(videoDuration - audioDuration),
      }
    );

    const moov = inspectMoovPlacement(file);
    addCheck(checks, 'warn', moov.faststartLikely, 'mp4_faststart_moov_before_mdat', moov);

    const blackLog = video ? await runFilter('blackdetect=d=1:pix_th=0.10') : '';
    const freezeLog = video ? await runFilter('freezedetect=n=-60dB:d=2') : '';
    const silenceLog = audio ? await runAudioFilter('silencedetect=noise=-45dB:d=1') : '';
    const volumeLog = audio ? await runAudioFilter('volumedetect') : '';
    const loudnessLog = audio ? await runAudioFilter('ebur128=peak=true') : '';
    const blackIntervals = parseFfmpegIntervals(blackLog, 'black');
    const freezeIntervals = parseFfmpegIntervals(freezeLog, 'freeze');
    const silenceIntervals = parseFfmpegIntervals(silenceLog, 'silence');
    const volume = parseVolumeDetect(volumeLog);
    const integratedLufs = parseIntegratedLufs(loudnessLog);

    addCheck(checks, 'warn', blackIntervals.length === 0, 'no_black_intervals_over_1s', {
      intervals: blackIntervals,
    });
    addCheck(checks, 'warn', freezeIntervals.length === 0, 'no_freeze_intervals_over_2s', {
      intervals: freezeIntervals,
    });
    const endSilence = silenceIntervals.find(
      (item) => item.end >= audioDuration - 0.2 && item.duration >= 2
    );
    addCheck(checks, 'hard', !endSilence, 'no_long_end_silence', {
      endSilence: endSilence || null,
      intervals: silenceIntervals,
    });
    if (volume.maxVolumeDb !== null) {
      addCheck(checks, 'warn', volume.maxVolumeDb <= -0.5, 'audio_peak_has_headroom', volume);
    }
    if (integratedLufs !== null) {
      addCheck(
        checks,
        'warn',
        integratedLufs >= -24 && integratedLufs <= -12,
        'integrated_loudness_story_sane',
        {
          integratedLufs,
          target: 'roughly -16 LUFS for narrated YouTube, warn range -24 to -12',
        }
      );
    }

    const srtInfo = parseSrt(srt);
    if (srtInfo) {
      addCheck(checks, 'hard', srtInfo.cues.length > 0, 'srt_has_cues', {
        cueCount: srtInfo.cues.length,
      });
      const srtIssues = validateSrtContinuity(srtInfo.cues);
      addCheck(checks, 'hard', srtIssues.length === 0, 'srt_cues_are_ordered_and_non_overlapping', {
        issues: srtIssues,
      });
      if (srtInfo.first) {
        addCheck(checks, 'warn', srtInfo.first.start <= 2, 'srt_starts_near_beginning', {
          firstStart: srtInfo.first.start,
        });
      }
      if (srtInfo.last) {
        const tailGap = audioDuration - srtInfo.last.end;
        addCheck(checks, 'hard', tailGap >= -0.5 && tailGap <= 8, 'srt_final_cue_near_audio_end', {
          lastEnd: srtInfo.last.end,
          audioDuration,
          tailGap,
        });
        addCheck(
          checks,
          'hard',
          /[.!?"']\s*$/.test(srtInfo.last.text),
          'srt_last_cue_ends_with_sentence_punctuation',
          {
            lastText: srtInfo.last.text,
          }
        );
      }
      const finalSource = finalSourceWordsPresent(sourceText, srtInfo.cues);
      if (finalSource) {
        addCheck(
          checks,
          'hard',
          finalSource.found,
          'source_text_final_words_present_in_final_captions',
          finalSource
        );
      }
    } else if (opts.strict) {
      addCheck(checks, 'hard', false, 'srt_required_in_strict_mode');
    }

    if (thumbnail) {
      const stat = fs.statSync(thumbnail);
      addCheck(checks, 'hard', stat.size <= 2 * 1024 * 1024, 'thumbnail_under_2mb', {
        bytes: stat.size,
      });
    } else if (opts.strict) {
      addCheck(checks, 'hard', false, 'thumbnail_required_in_strict_mode');
    }

    const metadata = parseMetadata(metadataPath);
    const youtube = metadataYoutube(metadata);
    if (youtube) {
      const title = String(youtube.title || '');
      const description = String(youtube.description || '');
      const tags = Array.isArray(youtube.tags) ? youtube.tags : [];
      addCheck(
        checks,
        'hard',
        title.length > 0 && title.length <= 100,
        'youtube_title_present_and_within_limit',
        {
          length: title.length,
        }
      );
      addCheck(checks, 'warn', title.length >= 20, 'youtube_title_descriptive_enough', {
        length: title.length,
      });
      addCheck(checks, 'hard', description.length <= 5000, 'youtube_description_within_limit', {
        length: description.length,
      });
      addCheck(checks, 'warn', description.length >= 120, 'youtube_description_not_empty_stub', {
        length: description.length,
      });
      addCheck(checks, 'warn', tags.length >= 3, 'youtube_tags_three_or_more', {
        tagCount: tags.length,
      });
      if (opts.story) {
        addCheck(checks, 'hard', hasYoutubeCta(description), 'story_youtube_treatment_has_cta', {
          searchedFor: [
            'subscribe',
            'notification bell',
            'like',
            'comment',
            'share',
            'next chapter',
          ],
        });
      }
    } else if (opts.strict || opts.story) {
      addCheck(checks, 'hard', false, 'metadata_required');
    }
    const chapters = collectChapters(metadata);
    if (chapters.length) {
      const first = chapterTimeSeconds(chapters[0].timestamp);
      addCheck(checks, 'hard', first === 0, 'chapters_start_at_00_00', {
        firstTimestamp: chapters[0].timestamp,
      });
      addCheck(checks, 'warn', chapters.length >= 3, 'youtube_chapters_three_or_more', {
        chapterCount: chapters.length,
      });
      let monotonic = true;
      let previous = -1;
      for (const chapter of chapters) {
        const seconds = chapterTimeSeconds(chapter.timestamp);
        if (seconds === null || seconds <= previous || seconds > formatDuration + 5)
          monotonic = false;
        previous = seconds ?? previous;
      }
      addCheck(checks, 'hard', monotonic, 'youtube_chapters_monotonic_and_within_duration', {
        chapters,
      });
    } else if (opts.strict) {
      addCheck(checks, 'hard', false, 'chapters_required_in_strict_mode');
    }
    if (opts.story) {
      addCheck(checks, 'hard', Boolean(srtInfo), 'story_requires_captions_for_upload');
      addCheck(checks, 'hard', chapters.length >= 3, 'story_requires_youtube_chapters');
      const endBlack = blackIntervals.find(
        (item) => item.end >= videoDuration - 0.2 && item.duration >= 2
      );
      const endFreeze = freezeIntervals.find(
        (item) => item.end >= videoDuration - 0.2 && item.duration >= 3
      );
      addCheck(checks, 'hard', !endBlack, 'story_final_seconds_not_black', {
        endBlack: endBlack || null,
      });
      addCheck(checks, 'hard', !endFreeze, 'story_final_seconds_not_frozen', {
        endFreeze: endFreeze || null,
      });
    }

    const hardFailures = checks.filter((check) => check.severity === 'hard' && !check.ok);
    const warnFailures = checks.filter((check) => check.severity === 'warn' && !check.ok);
    const score = readinessScore(checks);
    const result = {
      schema: 'scbe.video.quality_gate.v2',
      file,
      sha256: fileHash,
      format: probe.format || null,
      video: video || null,
      audio: audio || null,
      durations: { formatDuration, videoDuration, audioDuration },
      srt: srtInfo,
      thumbnail,
      metadata: metadataPath,
      sourceText,
      audioAnalysis: {
        volume,
        integratedLufs,
      },
      storyMode: Boolean(opts.story),
      checks,
      summary: {
        ok: hardFailures.length === 0,
        readinessScore: score,
        storyReady: Boolean(opts.story) ? hardFailures.length === 0 && score >= 80 : null,
        hardFailures: hardFailures.length,
        warnings: warnFailures.length,
      },
      verified_at: new Date().toISOString(),
    };

    const json = JSON.stringify(result, null, 2) + '\n';
    if (opts.out) {
      fs.writeFileSync(path.resolve(opts.out), json, 'utf8');
      console.log('Wrote quality gate report to', path.resolve(opts.out));
    } else {
      console.log(json);
    }
    process.exit(hardFailures.length ? 1 : 0);
  } catch (err) {
    console.error('quality gate failed:', String(err));
    process.exit(2);
  }
})();
