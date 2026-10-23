/**
 * Sentence-function bytes beside a conserved identity.
 *
 * The Essay 1 guide supplies the codes. This module copies them into a side
 * channel. It does not rewrite the identity bytes, and it does not call the
 * 14-layer pipeline or nested-patch attention.
 *
 * Essay prose is not in the catalog. Callers pass the bytes they want to test.
 */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export const SENTENCE_BYTE_FIELD_MAGIC = [0x53, 0x46, 0x42, 0x31] as const;
export const SENTENCE_BYTE_FIELD_VERSION = 1;
export const SENTENCE_BYTE_CHANNELS = [
  "paragraph",
  "sort",
  "slot",
  "job",
  "phrase",
] as const;

export type SentenceByteChannel = (typeof SENTENCE_BYTE_CHANNELS)[number];

interface CodeName {
  code: number;
  name: string;
}

interface SentenceRow {
  id: number;
  paragraph: number;
  ref: string;
  slot: number;
  sort: number;
  job: number;
  phrases: number[];
}

interface Catalog {
  sorts: CodeName[];
  slots: CodeName[];
  jobs: CodeName[];
  phrases: CodeName[];
  sentences: SentenceRow[];
}

export interface SentenceByteField {
  sentenceId: number;
  paragraph: number;
  slot: number;
  sort: number;
  job: number;
  phrases: number[];
  spans: Array<[number, number]>;
  identity: Uint8Array;
  channels: Record<SentenceByteChannel, Uint8Array>;
}

const catalog = JSON.parse(
  readFileSync(
    join(
      dirname(fileURLToPath(import.meta.url)),
      "sentenceFunctionCatalog.json",
    ),
    "utf8",
  ),
) as Catalog;

const sentences = new Map(catalog.sentences.map((row) => [row.id, row]));

const vocabulary: Record<SentenceByteChannel, number> = {
  paragraph: Math.max(...catalog.sentences.map((row) => row.paragraph)),
  sort: Math.max(...catalog.sorts.map((row) => row.code)),
  slot: Math.max(...catalog.slots.map((row) => row.code)),
  job: Math.max(...catalog.jobs.map((row) => row.code)),
  phrase: Math.max(...catalog.phrases.map((row) => row.code)),
};

function paint(
  identityLength: number,
  phraseCodes: number[],
  spans: Array<[number, number]>,
): Uint8Array {
  const channel = new Uint8Array(identityLength);
  const seen = new Uint8Array(identityLength);
  spans.forEach(([start, end], spanIndex) => {
    if (start < 0 || end > identityLength || end <= start) {
      throw new RangeError("phrase span is outside the identity");
    }
    for (let index = start; index < end; index += 1) {
      if (seen[index]) throw new RangeError("phrase spans overlap");
      seen[index] = 1;
      channel[index] = phraseCodes[spanIndex];
    }
  });
  return channel;
}

function pushU32(target: number[], value: number): void {
  if (value < 0 || value > 0xffffffff)
    throw new RangeError("integer does not fit in uint32");
  target.push(
    value & 0xff,
    (value >>> 8) & 0xff,
    (value >>> 16) & 0xff,
    (value >>> 24) & 0xff,
  );
}

function readU32(blob: Uint8Array, cursor: number): [number, number] {
  if (cursor + 4 > blob.length) throw new RangeError("byte field ended early");
  const value =
    blob[cursor] |
    (blob[cursor + 1] << 8) |
    (blob[cursor + 2] << 16) |
    (blob[cursor + 3] << 24);
  return [value >>> 0, cursor + 4];
}

function repeat(code: number, width: number): Uint8Array {
  return new Uint8Array(width).fill(code);
}

export function encodeSentenceByteField(
  identity: Uint8Array,
  sentenceId: number,
  phraseSpans?: Array<[number, number]>,
): Uint8Array {
  const row = sentences.get(sentenceId);
  if (!row) throw new RangeError(`sentence ${sentenceId} is not in the guide`);
  const phraseCodes = row.phrases;
  if (phraseCodes.length > 255)
    throw new RangeError("phrase list does not fit in one byte");
  const spans = phraseSpans ?? [];
  if (phraseSpans && spans.length !== phraseCodes.length) {
    throw new RangeError(
      "phrase spans must cover every phrase function on the sentence",
    );
  }
  const phraseChannel = paint(identity.length, phraseCodes, spans);
  const channels: Record<SentenceByteChannel, Uint8Array> = {
    paragraph: repeat(row.paragraph, identity.length),
    sort: repeat(row.sort, identity.length),
    slot: repeat(row.slot, identity.length),
    job: repeat(row.job, identity.length),
    phrase: phraseChannel,
  };
  const header: number[] = [
    ...SENTENCE_BYTE_FIELD_MAGIC,
    SENTENCE_BYTE_FIELD_VERSION,
    row.id,
    row.paragraph,
    row.slot,
    row.sort,
    row.job,
    phraseCodes.length,
    ...phraseCodes,
    spans.length,
  ];
  spans.forEach(([start, end]) => {
    pushU32(header, start);
    pushU32(header, end);
  });
  pushU32(header, identity.length);
  const body = Buffer.concat([
    Buffer.from(header),
    Buffer.from(identity),
    ...SENTENCE_BYTE_CHANNELS.map((name) => Buffer.from(channels[name])),
  ]);
  return new Uint8Array(body);
}

export function decodeSentenceByteField(blob: Uint8Array): SentenceByteField {
  if (
    blob.length < 4 ||
    SENTENCE_BYTE_FIELD_MAGIC.some((byte, index) => blob[index] !== byte)
  ) {
    throw new RangeError("byte field magic is not SFB1");
  }
  let cursor = 4;
  if (blob[cursor] !== SENTENCE_BYTE_FIELD_VERSION)
    throw new RangeError("unsupported byte field version");
  cursor += 1;
  if (cursor + 6 > blob.length) throw new RangeError("byte field ended early");
  const sentenceId = blob[cursor];
  const paragraph = blob[cursor + 1];
  const slot = blob[cursor + 2];
  const sort = blob[cursor + 3];
  const job = blob[cursor + 4];
  const phraseCount = blob[cursor + 5];
  cursor += 6;
  if (cursor + phraseCount > blob.length)
    throw new RangeError("byte field ended early");
  const phrases = Array.from(blob.slice(cursor, cursor + phraseCount));
  cursor += phraseCount;
  if (cursor >= blob.length) throw new RangeError("byte field ended early");
  const spanCount = blob[cursor];
  cursor += 1;
  const spans: Array<[number, number]> = [];
  for (let index = 0; index < spanCount; index += 1) {
    const [start, afterStart] = readU32(blob, cursor);
    const [end, afterEnd] = readU32(blob, afterStart);
    spans.push([start, end]);
    cursor = afterEnd;
  }
  const [identityLength, identityStart] = readU32(blob, cursor);
  const identityEnd = identityStart + identityLength;
  const channelEnd =
    identityEnd + identityLength * SENTENCE_BYTE_CHANNELS.length;
  if (channelEnd !== blob.length || identityEnd > blob.length) {
    throw new RangeError("byte field length does not match its channels");
  }
  const identity = blob.slice(identityStart, identityEnd);
  const channels = {} as Record<SentenceByteChannel, Uint8Array>;
  cursor = identityEnd;
  SENTENCE_BYTE_CHANNELS.forEach((name) => {
    channels[name] = blob.slice(cursor, cursor + identityLength);
    cursor += identityLength;
  });
  const expected: Record<SentenceByteChannel, Uint8Array> = {
    paragraph: repeat(paragraph, identityLength),
    sort: repeat(sort, identityLength),
    slot: repeat(slot, identityLength),
    job: repeat(job, identityLength),
    phrase: paint(identityLength, phrases, spans),
  };
  SENTENCE_BYTE_CHANNELS.forEach((name) => {
    if (channels[name].some((byte, index) => byte !== expected[name][index])) {
      throw new RangeError(`${name} channel does not match the header`);
    }
  });
  return {
    sentenceId,
    paragraph,
    slot,
    sort,
    job,
    phrases,
    spans,
    identity,
    channels,
  };
}

export function matchesGuide(decoded: SentenceByteField): boolean {
  const row = sentences.get(decoded.sentenceId);
  if (!row) return false;
  return (
    decoded.paragraph === row.paragraph &&
    decoded.slot === row.slot &&
    decoded.sort === row.sort &&
    decoded.job === row.job &&
    decoded.phrases.length === row.phrases.length &&
    decoded.phrases.every((code, index) => code === row.phrases[index])
  );
}

export function identityBytes(blob: Uint8Array): Uint8Array {
  return decodeSentenceByteField(blob).identity;
}

function permutation(size: number, seed: number): Map<number, number> {
  const items = Array.from({ length: size }, (_, index) => index + 1);
  let state = seed >>> 0;
  for (let index = size - 1; index > 0; index -= 1) {
    state = (Math.imul(1664525, state) + 1013904223) >>> 0;
    const swap = state % (index + 1);
    const held = items[index];
    items[index] = items[swap];
    items[swap] = held;
  }
  return new Map(items.map((code, index) => [index + 1, code]));
}

export function permuteByteField(
  blob: Uint8Array,
  channel: SentenceByteChannel,
  seed: number,
): Uint8Array {
  const decoded = decodeSentenceByteField(blob);
  const mapping = permutation(vocabulary[channel], seed);
  const phrases =
    channel === "phrase"
      ? decoded.phrases.map((code) => mapping.get(code) ?? code)
      : decoded.phrases.slice();
  const paragraph =
    channel === "paragraph"
      ? mapping.get(decoded.paragraph)!
      : decoded.paragraph;
  const sort = channel === "sort" ? mapping.get(decoded.sort)! : decoded.sort;
  const slot = channel === "slot" ? mapping.get(decoded.slot)! : decoded.slot;
  const job = channel === "job" ? mapping.get(decoded.job)! : decoded.job;
  const phraseChannel = paint(decoded.identity.length, phrases, decoded.spans);
  const channels: Record<SentenceByteChannel, Uint8Array> = {
    paragraph: repeat(paragraph, decoded.identity.length),
    sort: repeat(sort, decoded.identity.length),
    slot: repeat(slot, decoded.identity.length),
    job: repeat(job, decoded.identity.length),
    phrase: phraseChannel,
  };
  const header: number[] = [
    ...SENTENCE_BYTE_FIELD_MAGIC,
    SENTENCE_BYTE_FIELD_VERSION,
    decoded.sentenceId,
    paragraph,
    slot,
    sort,
    job,
    phrases.length,
    ...phrases,
    decoded.spans.length,
  ];
  decoded.spans.forEach(([start, end]) => {
    pushU32(header, start);
    pushU32(header, end);
  });
  pushU32(header, decoded.identity.length);
  return new Uint8Array(
    Buffer.concat([
      Buffer.from(header),
      Buffer.from(decoded.identity),
      ...SENTENCE_BYTE_CHANNELS.map((name) => Buffer.from(channels[name])),
    ]),
  );
}

export function guideSentenceCount(): number {
  return catalog.sentences.length;
}
