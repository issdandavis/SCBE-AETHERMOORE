/**
 * Deterministic, offline-verifiable source manifests for SCBE-AETHERMOORE.
 *
 * The manifest commits to Git index blob bytes rather than working-tree bytes.
 * That keeps the result stable across checkout line-ending policies. Detached
 * Ed25519 signatures provide an authority outside GitHub; hashes alone only
 * detect accidental changes when an attacker can replace both file and hash.
 */

import { spawn, spawnSync } from 'node:child_process';
import {
  createHash,
  createPrivateKey,
  createPublicKey,
  generateKeyPairSync,
  sign as cryptoSign,
  verify as cryptoVerify,
  type KeyObject,
} from 'node:crypto';
import { createReadStream, lstatSync, promises as fs, readlinkSync, statSync } from 'node:fs';
import path from 'node:path';
import type { Readable } from 'node:stream';

export const MANIFEST_SCHEMA = 'scbe.source-manifest.v1';
export const SIGNATURE_SCHEMA = 'scbe.source-manifest-signature.v1';
export const TREE_ALGORITHM = 'rfc6962-sha256:SCBE-SOURCE-ENTRY-v1';

export const DEFAULT_EXCLUSIONS = [
  'integrity/scbe-source-manifest.json',
  'integrity/scbe-source-manifest.sig.json',
] as const;

export type ManifestEntryKind = 'blob' | 'symlink' | 'gitlink';

export interface ManifestEntry {
  path: string;
  mode: string;
  kind: ManifestEntryKind;
  bytes: number;
  sha256: string;
  gitObject: string;
}

export interface ManifestSummary {
  entryCount: number;
  totalBytes: number;
  blobCount: number;
  symlinkCount: number;
  gitlinkCount: number;
}

export interface SourceManifest {
  schema: typeof MANIFEST_SCHEMA;
  repository: string;
  scope: 'git-index';
  hashAlgorithm: 'sha256';
  treeAlgorithm: typeof TREE_ALGORITHM;
  exclusions: string[];
  summary: ManifestSummary;
  merkleRoot: string;
  entries: ManifestEntry[];
}

export interface DetachedManifestSignature {
  schema: typeof SIGNATURE_SCHEMA;
  algorithm: 'Ed25519';
  keyFingerprint: string;
  manifestSha256: string;
  signatureBase64: string;
}

export interface VerificationResult {
  ok: boolean;
  issues: string[];
  warnings: string[];
  merkleRoot: string;
}

interface GitIndexRecord {
  mode: string;
  objectId: string;
  stage: number;
  path: string;
}

interface GitObjectDigest {
  bytes: number;
  sha256: string;
}

const HEX_256 = /^[0-9a-f]{64}$/;
const GIT_OBJECT_ID = /^[0-9a-f]{40,64}$/;
const textDecoder = new TextDecoder('utf-8', { fatal: true });

function sha256(data: Uint8Array | string): string {
  return createHash('sha256').update(data).digest('hex');
}

function compareUtf8(left: string, right: string): number {
  return Buffer.compare(Buffer.from(left, 'utf8'), Buffer.from(right, 'utf8'));
}

function normalizeRepoPath(value: string): string {
  if (!value || value.includes('\0') || value.includes('\\')) {
    throw new Error(`invalid repository path: ${JSON.stringify(value)}`);
  }
  if (value.startsWith('/') || /^[A-Za-z]:/.test(value)) {
    throw new Error(`repository path must be relative: ${value}`);
  }
  const normalized = path.posix.normalize(value);
  if (normalized !== value || normalized === '..' || normalized.startsWith('../')) {
    throw new Error(`repository path is not canonical: ${value}`);
  }
  return value;
}

function modeKind(mode: string): ManifestEntryKind {
  if (mode === '120000') return 'symlink';
  if (mode === '160000') return 'gitlink';
  if (mode === '100644' || mode === '100755') return 'blob';
  throw new Error(`unsupported Git index mode: ${mode}`);
}

function runGitBuffer(repoRoot: string, args: string[]): Buffer {
  const result = spawnSync('git', args, {
    cwd: repoRoot,
    encoding: 'buffer',
    maxBuffer: 64 * 1024 * 1024,
    windowsHide: true,
  });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error(`git ${args.join(' ')} failed: ${result.stderr.toString('utf8').trim()}`);
  }
  return result.stdout;
}

export function listGitIndex(repoRoot: string): GitIndexRecord[] {
  const raw = runGitBuffer(repoRoot, ['ls-files', '--stage', '-z']);
  const records: GitIndexRecord[] = [];
  let start = 0;
  for (let index = 0; index <= raw.length; index += 1) {
    if (index !== raw.length && raw[index] !== 0) continue;
    if (index === start) {
      start = index + 1;
      continue;
    }
    const record = raw.subarray(start, index);
    start = index + 1;
    const tab = record.indexOf(0x09);
    if (tab < 0) throw new Error('malformed git ls-files record: missing tab');
    const metadata = record.subarray(0, tab).toString('ascii');
    const match = /^(\d{6}) ([0-9a-f]{40,64}) ([0-3])$/.exec(metadata);
    if (!match) throw new Error(`malformed git ls-files metadata: ${metadata}`);
    const repoPath = normalizeRepoPath(textDecoder.decode(record.subarray(tab + 1)));
    records.push({ mode: match[1], objectId: match[2], stage: Number(match[3]), path: repoPath });
  }
  records.sort((left, right) => compareUtf8(left.path, right.path));
  for (let index = 0; index < records.length; index += 1) {
    if (records[index].stage !== 0) {
      throw new Error(`unmerged Git index entry is not manifestable: ${records[index].path}`);
    }
    if (index > 0 && records[index - 1].path === records[index].path) {
      throw new Error(`duplicate Git index path: ${records[index].path}`);
    }
  }
  return records;
}

class AsyncByteReader {
  private readonly iterator: AsyncIterator<Buffer>;
  private buffer = Buffer.alloc(0);
  private ended = false;

  constructor(stream: Readable) {
    this.iterator = stream[Symbol.asyncIterator]() as AsyncIterator<Buffer>;
  }

  private async fill(): Promise<void> {
    if (this.buffer.length > 0 || this.ended) return;
    const next = await this.iterator.next();
    if (next.done) {
      this.ended = true;
      return;
    }
    // Copy into an owned ArrayBuffer-backed Buffer. This also avoids retaining
    // a large slab from the stream after only a small tail remains.
    this.buffer = Buffer.from(next.value);
  }

  async readLine(): Promise<string> {
    const chunks: Buffer[] = [];
    while (true) {
      await this.fill();
      if (this.buffer.length === 0 && this.ended) {
        throw new Error('unexpected end of git cat-file output while reading header');
      }
      const newline = this.buffer.indexOf(0x0a);
      if (newline >= 0) {
        chunks.push(this.buffer.subarray(0, newline));
        this.buffer = this.buffer.subarray(newline + 1);
        return Buffer.concat(chunks).toString('ascii');
      }
      chunks.push(this.buffer);
      this.buffer = Buffer.alloc(0);
    }
  }

  async consume(length: number, consumer: (chunk: Buffer) => void): Promise<void> {
    let remaining = length;
    while (remaining > 0) {
      await this.fill();
      if (this.buffer.length === 0 && this.ended) {
        throw new Error('unexpected end of git cat-file output while reading object');
      }
      const take = Math.min(remaining, this.buffer.length);
      consumer(this.buffer.subarray(0, take));
      this.buffer = this.buffer.subarray(take);
      remaining -= take;
    }
  }

  async readByte(): Promise<number> {
    let value = -1;
    await this.consume(1, (chunk) => {
      value = chunk[0];
    });
    return value;
  }
}

async function hashGitObjects(
  repoRoot: string,
  objectIds: string[]
): Promise<Map<string, GitObjectDigest>> {
  const unique = [...new Set(objectIds)].sort();
  if (unique.length === 0) return new Map();
  const child = spawn('git', ['cat-file', '--batch'], {
    cwd: repoRoot,
    stdio: ['pipe', 'pipe', 'pipe'],
    windowsHide: true,
  });
  let stderr = '';
  child.stderr.setEncoding('utf8');
  child.stderr.on('data', (chunk: string) => {
    stderr += chunk;
  });
  const exit = new Promise<number>((resolve, reject) => {
    child.once('error', reject);
    child.once('close', (code) => resolve(code ?? 1));
  });
  child.stdin.end(`${unique.join('\n')}\n`);

  const reader = new AsyncByteReader(child.stdout);
  const digests = new Map<string, GitObjectDigest>();
  for (const requested of unique) {
    const header = await reader.readLine();
    const match = /^([0-9a-f]{40,64}) ([a-z]+) (\d+)$/.exec(header);
    if (!match) throw new Error(`unexpected git cat-file header for ${requested}: ${header}`);
    const [, actual, objectType, sizeText] = match;
    if (actual !== requested || objectType !== 'blob') {
      throw new Error(`expected blob ${requested}, received ${actual} ${objectType}`);
    }
    const bytes = Number(sizeText);
    if (!Number.isSafeInteger(bytes) || bytes < 0)
      throw new Error(`invalid blob size: ${sizeText}`);
    const hash = createHash('sha256');
    await reader.consume(bytes, (chunk) => hash.update(chunk));
    if ((await reader.readByte()) !== 0x0a)
      throw new Error(`missing separator after Git object ${requested}`);
    digests.set(requested, { bytes, sha256: hash.digest('hex') });
  }
  const exitCode = await exit;
  if (exitCode !== 0)
    throw new Error(`git cat-file --batch failed (${exitCode}): ${stderr.trim()}`);
  return digests;
}

function u32(value: number): Buffer {
  const encoded = Buffer.alloc(4);
  encoded.writeUInt32BE(value);
  return encoded;
}

function u64(value: number): Buffer {
  const encoded = Buffer.alloc(8);
  encoded.writeBigUInt64BE(BigInt(value));
  return encoded;
}

function leafHash(entry: ManifestEntry): Buffer {
  const pathBytes = Buffer.from(entry.path, 'utf8');
  const kindCode = entry.kind === 'blob' ? 0 : entry.kind === 'symlink' ? 1 : 2;
  const payload = Buffer.concat([
    Buffer.from('SCBE-SOURCE-ENTRY-v1\0', 'ascii'),
    u32(pathBytes.length),
    pathBytes,
    Buffer.from(entry.mode, 'ascii'),
    Buffer.from([kindCode]),
    u64(entry.bytes),
    Buffer.from(entry.sha256, 'hex'),
  ]);
  return createHash('sha256')
    .update(Buffer.from([0]))
    .update(payload)
    .digest();
}

function merkleSubtree(leaves: Buffer[]): Buffer {
  if (leaves.length === 0) return createHash('sha256').update(Buffer.alloc(0)).digest();
  if (leaves.length === 1) return leaves[0];
  let split = 1;
  while (split * 2 < leaves.length) split *= 2;
  return createHash('sha256')
    .update(Buffer.from([1]))
    .update(merkleSubtree(leaves.slice(0, split)))
    .update(merkleSubtree(leaves.slice(split)))
    .digest();
}

export function computeMerkleRoot(entries: ManifestEntry[]): string {
  return merkleSubtree(entries.map(leafHash)).toString('hex');
}

function summarize(entries: ManifestEntry[]): ManifestSummary {
  return {
    entryCount: entries.length,
    totalBytes: entries.reduce((total, entry) => total + entry.bytes, 0),
    blobCount: entries.filter((entry) => entry.kind === 'blob').length,
    symlinkCount: entries.filter((entry) => entry.kind === 'symlink').length,
    gitlinkCount: entries.filter((entry) => entry.kind === 'gitlink').length,
  };
}

function canonicalExclusions(values: readonly string[]): string[] {
  return [...new Set(values.map(normalizeRepoPath))].sort(compareUtf8);
}

export async function buildSourceManifest(
  repoRoot: string,
  options: { repository?: string; exclusions?: readonly string[] } = {}
): Promise<SourceManifest> {
  const exclusions = canonicalExclusions(options.exclusions ?? DEFAULT_EXCLUSIONS);
  const excluded = new Set(exclusions);
  const records = listGitIndex(repoRoot).filter((record) => !excluded.has(record.path));
  const blobRecords = records.filter((record) => modeKind(record.mode) !== 'gitlink');
  const digests = await hashGitObjects(
    repoRoot,
    blobRecords.map((record) => record.objectId)
  );
  const entries = records.map((record): ManifestEntry => {
    const kind = modeKind(record.mode);
    if (kind === 'gitlink') {
      return {
        path: record.path,
        mode: record.mode,
        kind,
        bytes: 0,
        sha256: sha256(`SCBE-GITLINK-v1\0${record.objectId}`),
        gitObject: record.objectId,
      };
    }
    const digest = digests.get(record.objectId);
    if (!digest) throw new Error(`missing digest for Git object ${record.objectId}`);
    return {
      path: record.path,
      mode: record.mode,
      kind,
      bytes: digest.bytes,
      sha256: digest.sha256,
      gitObject: record.objectId,
    };
  });
  return {
    schema: MANIFEST_SCHEMA,
    repository: options.repository ?? 'issdandavis/SCBE-AETHERMOORE',
    scope: 'git-index',
    hashAlgorithm: 'sha256',
    treeAlgorithm: TREE_ALGORITHM,
    exclusions,
    summary: summarize(entries),
    merkleRoot: computeMerkleRoot(entries),
    entries,
  };
}

export function serializeManifest(manifest: SourceManifest): string {
  validateManifest(manifest);
  return `${JSON.stringify(manifest, null, 2)}\n`;
}

function sameSummary(left: ManifestSummary, right: ManifestSummary): boolean {
  return (
    left.entryCount === right.entryCount &&
    left.totalBytes === right.totalBytes &&
    left.blobCount === right.blobCount &&
    left.symlinkCount === right.symlinkCount &&
    left.gitlinkCount === right.gitlinkCount
  );
}

export function validateManifest(value: unknown): asserts value is SourceManifest {
  if (!value || typeof value !== 'object') throw new Error('manifest must be an object');
  const manifest = value as Partial<SourceManifest>;
  if (manifest.schema !== MANIFEST_SCHEMA)
    throw new Error(`unsupported manifest schema: ${manifest.schema}`);
  if (typeof manifest.repository !== 'string' || !manifest.repository)
    throw new Error('repository is required');
  if (manifest.scope !== 'git-index') throw new Error('manifest scope must be git-index');
  if (manifest.hashAlgorithm !== 'sha256')
    throw new Error('manifest hash algorithm must be sha256');
  if (manifest.treeAlgorithm !== TREE_ALGORITHM)
    throw new Error('unsupported Merkle tree algorithm');
  if (!Array.isArray(manifest.exclusions) || !Array.isArray(manifest.entries)) {
    throw new Error('manifest exclusions and entries must be arrays');
  }
  const exclusions = canonicalExclusions(manifest.exclusions);
  if (JSON.stringify(exclusions) !== JSON.stringify(manifest.exclusions)) {
    throw new Error('manifest exclusions must be canonical, unique, and UTF-8 sorted');
  }
  const excluded = new Set(exclusions);
  let previous = '';
  for (const [index, entry] of manifest.entries.entries()) {
    if (!entry || typeof entry !== 'object') throw new Error(`entry ${index} must be an object`);
    normalizeRepoPath(entry.path);
    if (index > 0 && compareUtf8(previous, entry.path) >= 0) {
      throw new Error(`manifest entries are not strictly UTF-8 sorted at ${entry.path}`);
    }
    previous = entry.path;
    if (excluded.has(entry.path))
      throw new Error(`excluded path appears in entries: ${entry.path}`);
    if (modeKind(entry.mode) !== entry.kind)
      throw new Error(`mode/kind mismatch for ${entry.path}`);
    if (!Number.isSafeInteger(entry.bytes) || entry.bytes < 0)
      throw new Error(`invalid byte count for ${entry.path}`);
    if (!HEX_256.test(entry.sha256)) throw new Error(`invalid SHA-256 for ${entry.path}`);
    if (!GIT_OBJECT_ID.test(entry.gitObject))
      throw new Error(`invalid Git object ID for ${entry.path}`);
    if (entry.kind === 'gitlink' && entry.bytes !== 0)
      throw new Error(`gitlink bytes must be zero: ${entry.path}`);
  }
  const expectedSummary = summarize(manifest.entries);
  if (!manifest.summary || !sameSummary(manifest.summary, expectedSummary)) {
    throw new Error('manifest summary does not match entries');
  }
  const expectedRoot = computeMerkleRoot(manifest.entries);
  if (manifest.merkleRoot !== expectedRoot)
    throw new Error('manifest Merkle root does not match entries');
}

export function parseManifest(text: string): SourceManifest {
  const parsed: unknown = JSON.parse(text);
  validateManifest(parsed);
  return parsed;
}

function differenceIssues(expected: SourceManifest, actual: SourceManifest, limit = 100): string[] {
  const issues: string[] = [];
  const expectedByPath = new Map(expected.entries.map((entry) => [entry.path, entry]));
  const actualByPath = new Map(actual.entries.map((entry) => [entry.path, entry]));
  for (const [repoPath, expectedEntry] of expectedByPath) {
    const actualEntry = actualByPath.get(repoPath);
    if (!actualEntry) issues.push(`missing from Git index: ${repoPath}`);
    else if (JSON.stringify(actualEntry) !== JSON.stringify(expectedEntry))
      issues.push(`changed in Git index: ${repoPath}`);
    if (issues.length >= limit) return issues;
  }
  for (const repoPath of actualByPath.keys()) {
    if (!expectedByPath.has(repoPath)) issues.push(`unmanifested Git index path: ${repoPath}`);
    if (issues.length >= limit) return issues;
  }
  if (expected.merkleRoot !== actual.merkleRoot)
    issues.push('Git index Merkle root differs from manifest');
  return issues;
}

export async function verifyManifestAgainstGitIndex(
  manifest: SourceManifest,
  repoRoot: string
): Promise<VerificationResult> {
  validateManifest(manifest);
  const actual = await buildSourceManifest(repoRoot, {
    repository: manifest.repository,
    exclusions: manifest.exclusions,
  });
  const issues = differenceIssues(manifest, actual);
  return { ok: issues.length === 0, issues, warnings: [], merkleRoot: actual.merkleRoot };
}

async function hashFile(filePath: string): Promise<GitObjectDigest> {
  const hash = createHash('sha256');
  let bytes = 0;
  for await (const chunk of createReadStream(filePath)) {
    const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    bytes += buffer.length;
    hash.update(buffer);
  }
  return { bytes, sha256: hash.digest('hex') };
}

function localPath(repoRoot: string, repoPath: string): string {
  return path.join(repoRoot, ...repoPath.split('/'));
}

async function listFilesystemFiles(
  repoRoot: string,
  ignoredGitlinks: Set<string>,
  directory = repoRoot,
  prefix = ''
): Promise<string[]> {
  const files: string[] = [];
  const children = await fs.readdir(directory, { withFileTypes: true });
  children.sort((left, right) => compareUtf8(left.name, right.name));
  for (const child of children) {
    const repoPath = prefix ? `${prefix}/${child.name}` : child.name;
    if (repoPath === '.git' || repoPath.startsWith('.git/')) continue;
    if (ignoredGitlinks.has(repoPath)) continue;
    if (child.isDirectory()) {
      files.push(
        ...(await listFilesystemFiles(
          repoRoot,
          ignoredGitlinks,
          path.join(directory, child.name),
          repoPath
        ))
      );
    } else {
      files.push(repoPath);
    }
  }
  return files;
}

export async function verifyManifestAgainstFilesystem(
  manifest: SourceManifest,
  repoRoot: string,
  options: { allowUnverifiedGitlinks?: boolean } = {}
): Promise<VerificationResult> {
  validateManifest(manifest);
  const issues: string[] = [];
  const warnings: string[] = [];
  const actualEntries: ManifestEntry[] = [];
  const gitlinks = new Set(
    manifest.entries.filter((entry) => entry.kind === 'gitlink').map((entry) => entry.path)
  );

  for (const entry of manifest.entries) {
    const target = localPath(repoRoot, entry.path);
    if (entry.kind === 'gitlink') {
      const message = `gitlink content is not present in the parent manifest: ${entry.path}@${entry.gitObject}`;
      if (options.allowUnverifiedGitlinks) warnings.push(message);
      else issues.push(message);
      actualEntries.push(entry);
      continue;
    }
    let stats;
    try {
      stats = lstatSync(target);
    } catch {
      issues.push(`missing filesystem path: ${entry.path}`);
      continue;
    }
    let digest: GitObjectDigest;
    if (entry.kind === 'symlink') {
      if (!stats.isSymbolicLink()) {
        issues.push(`expected symbolic link: ${entry.path}`);
        continue;
      }
      const link = Buffer.from(readlinkSync(target), 'utf8');
      digest = { bytes: link.length, sha256: sha256(link) };
    } else {
      if (!stats.isFile()) {
        issues.push(`expected regular file: ${entry.path}`);
        continue;
      }
      digest = await hashFile(target);
      if (process.platform !== 'win32') {
        const executable = (statSync(target).mode & 0o111) !== 0;
        if ((entry.mode === '100755') !== executable)
          issues.push(`executable mode differs: ${entry.path}`);
      }
    }
    if (digest.bytes !== entry.bytes || digest.sha256 !== entry.sha256) {
      issues.push(`filesystem bytes differ: ${entry.path}`);
      continue;
    }
    actualEntries.push(entry);
  }

  const allowed = new Set([
    ...manifest.entries.filter((entry) => entry.kind !== 'gitlink').map((entry) => entry.path),
    ...manifest.exclusions,
  ]);
  for (const repoPath of await listFilesystemFiles(repoRoot, gitlinks)) {
    if (!allowed.has(repoPath)) issues.push(`unmanifested filesystem path: ${repoPath}`);
    if (issues.length >= 100) break;
  }
  return {
    ok: issues.length === 0,
    issues,
    warnings,
    merkleRoot: computeMerkleRoot(
      actualEntries.sort((left, right) => compareUtf8(left.path, right.path))
    ),
  };
}

function requireEd25519(key: KeyObject, label: string): KeyObject {
  if (key.asymmetricKeyType !== 'ed25519') throw new Error(`${label} must be an Ed25519 key`);
  return key;
}

export function publicKeyFingerprint(publicKeyPem: string | Buffer): string {
  const key = requireEd25519(createPublicKey(publicKeyPem), 'public key');
  const der = key.export({ type: 'spki', format: 'der' });
  return `ed25519-sha256:${sha256(der)}`;
}

export function createDetachedSignature(
  manifestBytes: Buffer,
  privateKeyPem: string | Buffer,
  passphrase?: string
): DetachedManifestSignature {
  const privateKey = requireEd25519(
    createPrivateKey({ key: privateKeyPem, format: 'pem', passphrase }),
    'private key'
  );
  const publicKey = createPublicKey({
    key: privateKey.export({ type: 'pkcs8', format: 'pem' }),
    format: 'pem',
  });
  return {
    schema: SIGNATURE_SCHEMA,
    algorithm: 'Ed25519',
    keyFingerprint: publicKeyFingerprint(publicKey.export({ type: 'spki', format: 'pem' })),
    manifestSha256: sha256(manifestBytes),
    signatureBase64: cryptoSign(null, manifestBytes, privateKey).toString('base64'),
  };
}

export function verifyDetachedSignature(
  manifestBytes: Buffer,
  signature: DetachedManifestSignature,
  publicKeyPem: string | Buffer
): boolean {
  if (
    signature.schema !== SIGNATURE_SCHEMA ||
    signature.algorithm !== 'Ed25519' ||
    signature.manifestSha256 !== sha256(manifestBytes)
  ) {
    return false;
  }
  const publicKey = requireEd25519(createPublicKey(publicKeyPem), 'public key');
  if (signature.keyFingerprint !== publicKeyFingerprint(publicKeyPem)) return false;
  let rawSignature: Buffer;
  try {
    rawSignature = Buffer.from(signature.signatureBase64, 'base64');
  } catch {
    return false;
  }
  return cryptoVerify(null, manifestBytes, publicKey, rawSignature);
}

export function serializeDetachedSignature(signature: DetachedManifestSignature): string {
  return `${JSON.stringify(signature, null, 2)}\n`;
}

export function parseDetachedSignature(text: string): DetachedManifestSignature {
  const parsed = JSON.parse(text) as Partial<DetachedManifestSignature>;
  if (
    parsed.schema !== SIGNATURE_SCHEMA ||
    parsed.algorithm !== 'Ed25519' ||
    typeof parsed.keyFingerprint !== 'string' ||
    typeof parsed.manifestSha256 !== 'string' ||
    typeof parsed.signatureBase64 !== 'string' ||
    !HEX_256.test(parsed.manifestSha256)
  ) {
    throw new Error('invalid detached manifest signature');
  }
  return parsed as DetachedManifestSignature;
}

export function generateEncryptedEd25519KeyPair(passphrase: string): {
  privateKeyPem: string;
  publicKeyPem: string;
  fingerprint: string;
} {
  if (passphrase.length < 16) throw new Error('key passphrase must contain at least 16 characters');
  const pair = generateKeyPairSync('ed25519');
  const privateKeyPem = pair.privateKey.export({
    type: 'pkcs8',
    format: 'pem',
    cipher: 'aes-256-cbc',
    passphrase,
  }) as string;
  const publicKeyPem = pair.publicKey.export({ type: 'spki', format: 'pem' }) as string;
  return { privateKeyPem, publicKeyPem, fingerprint: publicKeyFingerprint(publicKeyPem) };
}

export function isPathInside(parent: string, candidate: string): boolean {
  const relative = path.relative(path.resolve(parent), path.resolve(candidate));
  return (
    relative === '' ||
    (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))
  );
}

export function manifestSha256(manifestBytes: Uint8Array): string {
  return sha256(manifestBytes);
}
