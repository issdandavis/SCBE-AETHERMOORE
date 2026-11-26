import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { after, describe, test } from 'node:test';
import { promises as fs } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {
  buildSourceManifest,
  createDetachedSignature,
  generateEncryptedEd25519KeyPair,
  isPathInside,
  parseDetachedSignature,
  parseManifest,
  serializeDetachedSignature,
  serializeManifest,
  verifyDetachedSignature,
  verifyManifestAgainstFilesystem,
  verifyManifestAgainstGitIndex,
} from '../../src/integrity/repositoryManifest.ts';

const scratch: string[] = [];

test('repository integrity workflow does not name false as a cache package manager', async () => {
  const workflow = await fs.readFile(
    new URL('../../.github/workflows/repository-integrity.yml', import.meta.url),
    'utf8'
  );
  assert.doesNotMatch(workflow, /^\s*cache:\s*(?:false|["']false["'])\s*$/m);
});

test('automation cannot merge around the repository integrity check', async () => {
  const [trustedAutoMerge, agentRouter] = await Promise.all([
    fs.readFile(new URL('../../.github/workflows/auto-merge-enable.yml', import.meta.url), 'utf8'),
    fs.readFile(new URL('../../.github/workflows/agent-router.yml', import.meta.url), 'utf8'),
  ]);

  for (const workflow of [trustedAutoMerge, agentRouter]) {
    assert.match(workflow, /required_status_checks/);
    assert.match(workflow, /verify-source-manifest/);
    assert.doesNotMatch(workflow, /gh pr merge[^\n]*--admin/);
  }
  assert.match(trustedAutoMerge, /steps\.protection\.outputs\.safe_to_merge == 'true'/);
});

function git(repo: string, ...args: string[]): string {
  return execFileSync('git', args, { cwd: repo, encoding: 'utf8', windowsHide: true }).trim();
}

async function fixture(): Promise<string> {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'scbe-source-manifest-'));
  scratch.push(root);
  git(root, 'init', '--quiet');
  git(root, 'config', 'user.email', 'integrity-test@invalid.example');
  git(root, 'config', 'user.name', 'SCBE Integrity Test');
  git(root, 'config', 'core.autocrlf', 'false');
  await fs.mkdir(path.join(root, 'integrity'), { recursive: true });
  await fs.mkdir(path.join(root, 'src'), { recursive: true });
  await fs.writeFile(path.join(root, 'integrity', 'scbe-source-manifest.json'), '{}\n');
  await fs.writeFile(path.join(root, 'README.md'), '# fixture\n');
  await fs.writeFile(path.join(root, 'src', 'alpha.txt'), 'alpha\n');
  await fs.writeFile(path.join(root, 'src', 'unicode-φ.txt'), 'phi\n');
  git(root, 'add', '-A');
  git(root, 'commit', '--quiet', '-m', 'fixture');

  const commit = git(root, 'rev-parse', 'HEAD');
  git(root, 'update-index', '--add', '--cacheinfo', `160000,${commit},vendor/dependency`);
  return root;
}

after(async () => {
  await Promise.all(scratch.map((root) => fs.rm(root, { recursive: true, force: true })));
});

describe('source manifest', () => {
  test('is deterministic, sorted, and records gitlinks without pretending they are files', async () => {
    const repo = await fixture();
    const first = await buildSourceManifest(repo, { repository: 'fixture/repo' });
    const second = await buildSourceManifest(repo, { repository: 'fixture/repo' });

    assert.equal(serializeManifest(first), serializeManifest(second));
    assert.equal(
      first.entries.some((entry) => entry.path === 'integrity/scbe-source-manifest.json'),
      false
    );
    assert.deepEqual(
      first.entries.map((entry) => entry.path),
      [...first.entries.map((entry) => entry.path)].sort((left, right) =>
        Buffer.compare(Buffer.from(left), Buffer.from(right))
      )
    );
    const gitlink = first.entries.find((entry) => entry.path === 'vendor/dependency');
    assert.equal(gitlink?.kind, 'gitlink');
    assert.equal(gitlink?.mode, '160000');
    assert.equal(gitlink?.bytes, 0);
    assert.equal(first.summary.gitlinkCount, 1);
    assert.equal(first.merkleRoot.length, 64);
  });

  test('distinguishes committed/index bytes from mutable working-tree bytes', async () => {
    const repo = await fixture();
    const manifest = await buildSourceManifest(repo);

    assert.equal((await verifyManifestAgainstGitIndex(manifest, repo)).ok, true);
    const cleanFilesystem = await verifyManifestAgainstFilesystem(manifest, repo, {
      allowUnverifiedGitlinks: true,
    });
    assert.equal(cleanFilesystem.ok, true);
    assert.equal(cleanFilesystem.warnings.length, 1);

    await fs.writeFile(path.join(repo, 'src', 'alpha.txt'), 'tampered but not staged\n');
    assert.equal((await verifyManifestAgainstGitIndex(manifest, repo)).ok, true);
    const tamperedFilesystem = await verifyManifestAgainstFilesystem(manifest, repo, {
      allowUnverifiedGitlinks: true,
    });
    assert.equal(tamperedFilesystem.ok, false);
    assert.match(tamperedFilesystem.issues.join('\n'), /filesystem bytes differ: src\/alpha\.txt/);

    git(repo, 'add', 'src/alpha.txt');
    const changedIndex = await verifyManifestAgainstGitIndex(manifest, repo);
    assert.equal(changedIndex.ok, false);
    assert.match(changedIndex.issues.join('\n'), /changed in Git index: src\/alpha\.txt/);
  });

  test('fails closed for extra archive files and unacknowledged gitlinks', async () => {
    const repo = await fixture();
    const manifest = await buildSourceManifest(repo);
    const strict = await verifyManifestAgainstFilesystem(manifest, repo);
    assert.equal(strict.ok, false);
    assert.match(strict.issues.join('\n'), /gitlink content is not present/);

    await fs.writeFile(path.join(repo, 'surprise.bin'), 'not declared\n');
    const withExtra = await verifyManifestAgainstFilesystem(manifest, repo, {
      allowUnverifiedGitlinks: true,
    });
    assert.equal(withExtra.ok, false);
    assert.match(withExtra.issues.join('\n'), /unmanifested filesystem path: surprise\.bin/);
  });

  test('rejects a manifest whose entry changed without a matching root', async () => {
    const repo = await fixture();
    const manifest = await buildSourceManifest(repo);
    const tampered = JSON.parse(serializeManifest(manifest));
    tampered.entries[0].sha256 = '0'.repeat(64);
    assert.throws(
      () => parseManifest(JSON.stringify(tampered)),
      /Merkle root does not match entries/
    );
  });

  test('rejects path traversal before touching the filesystem', async () => {
    const repo = await fixture();
    const manifest = await buildSourceManifest(repo);
    const tampered = JSON.parse(serializeManifest(manifest));
    tampered.entries[0].path = '../escape';
    assert.throws(() => parseManifest(JSON.stringify(tampered)), /path is not canonical/);
  });
});

describe('detached Ed25519 authority', () => {
  test('verifies the exact manifest bytes and rejects wrong bytes or key', () => {
    const passphrase = 'correct horse battery staple';
    const pair = generateEncryptedEd25519KeyPair(passphrase);
    const other = generateEncryptedEd25519KeyPair('another sufficiently long passphrase');
    const bytes = Buffer.from('{"manifest":"exact bytes"}\n');
    const signature = createDetachedSignature(bytes, pair.privateKeyPem, passphrase);

    assert.equal(verifyDetachedSignature(bytes, signature, pair.publicKeyPem), true);
    assert.equal(
      verifyDetachedSignature(
        Buffer.concat([bytes, Buffer.from('x')]),
        signature,
        pair.publicKeyPem
      ),
      false
    );
    assert.equal(verifyDetachedSignature(bytes, signature, other.publicKeyPem), false);
    assert.deepEqual(parseDetachedSignature(serializeDetachedSignature(signature)), signature);
  });

  test('recognizes private-key paths inside the repository boundary', () => {
    const root = path.resolve('C:/repo');
    assert.equal(isPathInside(root, path.join(root, 'keys', 'private.pem')), true);
    assert.equal(isPathInside(root, path.resolve('C:/offline/private.pem')), false);
  });
});
