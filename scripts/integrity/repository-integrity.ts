#!/usr/bin/env node

import { promises as fs } from 'node:fs';
import path from 'node:path';
import {
  buildSourceManifest,
  createDetachedSignature,
  generateEncryptedEd25519KeyPair,
  isPathInside,
  manifestSha256,
  parseDetachedSignature,
  parseManifest,
  publicKeyFingerprint,
  serializeDetachedSignature,
  serializeManifest,
  verifyDetachedSignature,
  verifyManifestAgainstFilesystem,
  verifyManifestAgainstGitIndex,
} from '../../src/integrity/repositoryManifest.ts';

interface ParsedArguments {
  command: string;
  values: Map<string, string>;
  flags: Set<string>;
}

const USAGE = `SCBE repository integrity

Usage:
  node scripts/integrity/repository-integrity.ts generate [--repo PATH] [--output PATH]
  node scripts/integrity/repository-integrity.ts verify [--repo PATH] [--manifest PATH]
       [--source git-index|filesystem] [--allow-unverified-gitlinks]
  node scripts/integrity/repository-integrity.ts keygen --private-key PATH --public-key PATH [--repo PATH]
  node scripts/integrity/repository-integrity.ts sign --private-key PATH [--manifest PATH]
       [--signature PATH] [--repo PATH]
  node scripts/integrity/repository-integrity.ts verify-signature --public-key PATH
       [--manifest PATH] [--signature PATH] [--repo PATH]
  node scripts/integrity/repository-integrity.ts fingerprint --public-key PATH

Key generation and signing read the passphrase from SCBE_INTEGRITY_KEY_PASSPHRASE.
The private key is refused when its path is inside the repository.
`;

function parseArguments(argv: string[]): ParsedArguments {
  const command = argv[0] ?? '';
  const values = new Map<string, string>();
  const flags = new Set<string>();
  for (let index = 1; index < argv.length; index += 1) {
    const item = argv[index];
    if (!item.startsWith('--')) throw new Error(`unexpected positional argument: ${item}`);
    if (item === '--allow-unverified-gitlinks') {
      flags.add(item);
      continue;
    }
    const value = argv[index + 1];
    if (!value || value.startsWith('--')) throw new Error(`missing value for ${item}`);
    values.set(item, value);
    index += 1;
  }
  return { command, values, flags };
}

function required(args: ParsedArguments, name: string): string {
  const value = args.values.get(name);
  if (!value) throw new Error(`${name} is required`);
  return value;
}

function resolvedRepo(args: ParsedArguments): string {
  return path.resolve(args.values.get('--repo') ?? process.cwd());
}

function manifestPath(args: ParsedArguments, repoRoot: string): string {
  return path.resolve(
    args.values.get('--manifest') ?? path.join(repoRoot, 'integrity', 'scbe-source-manifest.json')
  );
}

function signaturePath(args: ParsedArguments, repoRoot: string): string {
  return path.resolve(
    args.values.get('--signature') ??
      path.join(repoRoot, 'integrity', 'scbe-source-manifest.sig.json')
  );
}

async function writeAtomic(target: string, data: string): Promise<void> {
  await fs.mkdir(path.dirname(target), { recursive: true });
  const temporary = path.join(path.dirname(target), `.${path.basename(target)}.${process.pid}.tmp`);
  await fs.writeFile(temporary, data, { encoding: 'utf8', flag: 'wx' });
  try {
    await fs.rename(temporary, target);
  } catch (error) {
    const code = (error as NodeJS.ErrnoException).code;
    if (code !== 'EEXIST' && code !== 'EPERM') throw error;
    await fs.rm(target, { force: true });
    await fs.rename(temporary, target);
  }
}

function print(value: unknown): void {
  process.stdout.write(`${JSON.stringify(value, null, 2)}\n`);
}

async function generate(args: ParsedArguments): Promise<void> {
  const repoRoot = resolvedRepo(args);
  const output = path.resolve(args.values.get('--output') ?? manifestPath(args, repoRoot));
  const manifest = await buildSourceManifest(repoRoot);
  const serialized = serializeManifest(manifest);
  await writeAtomic(output, serialized);
  print({
    status: 'generated',
    output,
    manifestSha256: manifestSha256(Buffer.from(serialized, 'utf8')),
    merkleRoot: manifest.merkleRoot,
    ...manifest.summary,
  });
}

async function verify(args: ParsedArguments): Promise<void> {
  const repoRoot = resolvedRepo(args);
  const source = args.values.get('--source') ?? 'git-index';
  if (source !== 'git-index' && source !== 'filesystem') {
    throw new Error('--source must be git-index or filesystem');
  }
  const target = manifestPath(args, repoRoot);
  const manifest = parseManifest(await fs.readFile(target, 'utf8'));
  const result =
    source === 'git-index'
      ? await verifyManifestAgainstGitIndex(manifest, repoRoot)
      : await verifyManifestAgainstFilesystem(manifest, repoRoot, {
          allowUnverifiedGitlinks: args.flags.has('--allow-unverified-gitlinks'),
        });
  print({ status: result.ok ? 'verified' : 'failed', source, manifest: target, ...result });
  if (!result.ok) process.exitCode = 2;
}

async function keygen(args: ParsedArguments): Promise<void> {
  const repoRoot = resolvedRepo(args);
  const privatePath = path.resolve(required(args, '--private-key'));
  const publicPath = path.resolve(required(args, '--public-key'));
  if (isPathInside(repoRoot, privatePath))
    throw new Error('private key path must be outside the repository');
  const passphrase = process.env.SCBE_INTEGRITY_KEY_PASSPHRASE ?? '';
  const pair = generateEncryptedEd25519KeyPair(passphrase);
  await fs.mkdir(path.dirname(privatePath), { recursive: true });
  await fs.mkdir(path.dirname(publicPath), { recursive: true });
  await fs.writeFile(privatePath, pair.privateKeyPem, {
    encoding: 'utf8',
    flag: 'wx',
    mode: 0o600,
  });
  try {
    await fs.writeFile(publicPath, pair.publicKeyPem, {
      encoding: 'utf8',
      flag: 'wx',
      mode: 0o644,
    });
  } catch (error) {
    await fs.rm(privatePath, { force: true });
    throw error;
  }
  print({
    status: 'key-created',
    privateKey: privatePath,
    publicKey: publicPath,
    fingerprint: pair.fingerprint,
  });
}

async function sign(args: ParsedArguments): Promise<void> {
  const repoRoot = resolvedRepo(args);
  const privatePath = path.resolve(required(args, '--private-key'));
  if (isPathInside(repoRoot, privatePath))
    throw new Error('private key path must be outside the repository');
  const targetManifest = manifestPath(args, repoRoot);
  const output = signaturePath(args, repoRoot);
  const manifestBytes = await fs.readFile(targetManifest);
  parseManifest(manifestBytes.toString('utf8'));
  const privateKey = await fs.readFile(privatePath);
  const signature = createDetachedSignature(
    manifestBytes,
    privateKey,
    process.env.SCBE_INTEGRITY_KEY_PASSPHRASE
  );
  await writeAtomic(output, serializeDetachedSignature(signature));
  print({ status: 'signed', manifest: targetManifest, signature: output, ...signature });
}

async function verifySignature(args: ParsedArguments): Promise<void> {
  const repoRoot = resolvedRepo(args);
  const targetManifest = manifestPath(args, repoRoot);
  const targetSignature = signaturePath(args, repoRoot);
  const publicPath = path.resolve(required(args, '--public-key'));
  const manifestBytes = await fs.readFile(targetManifest);
  parseManifest(manifestBytes.toString('utf8'));
  const signature = parseDetachedSignature(await fs.readFile(targetSignature, 'utf8'));
  const publicKey = await fs.readFile(publicPath);
  const ok = verifyDetachedSignature(manifestBytes, signature, publicKey);
  print({
    status: ok ? 'verified' : 'failed',
    manifest: targetManifest,
    signature: targetSignature,
    publicKey: publicPath,
  });
  if (!ok) process.exitCode = 2;
}

async function fingerprint(args: ParsedArguments): Promise<void> {
  const publicPath = path.resolve(required(args, '--public-key'));
  print({
    publicKey: publicPath,
    fingerprint: publicKeyFingerprint(await fs.readFile(publicPath)),
  });
}

async function main(): Promise<void> {
  const args = parseArguments(process.argv.slice(2));
  if (args.command === 'generate') return generate(args);
  if (args.command === 'verify') return verify(args);
  if (args.command === 'keygen') return keygen(args);
  if (args.command === 'sign') return sign(args);
  if (args.command === 'verify-signature') return verifySignature(args);
  if (args.command === 'fingerprint') return fingerprint(args);
  process.stdout.write(USAGE);
  if (args.command && args.command !== 'help' && args.command !== '--help') process.exitCode = 2;
}

main().catch((error: unknown) => {
  const message = error instanceof Error ? error.message : String(error);
  process.stderr.write(`repository-integrity: ${message}\n`);
  if (process.env.SCBE_INTEGRITY_DEBUG === '1' && error instanceof Error) {
    process.stderr.write(`${error.stack ?? ''}\n`);
  }
  process.exitCode = 1;
});
