# SCBE Repository Integrity

Status: IMPLEMENTED source-manifest mechanics; offline owner signature not yet
provisioned

## Security result

SCBE now has one deterministic source manifest for the complete Git index. Each
tracked path is represented by its UTF-8 path, Git mode, kind, byte length,
SHA-256 digest, and Git object ID. Domain-separated leaf hashes are joined with
the RFC 6962 tree shape into one Merkle root.

The manifest is stored at `integrity/scbe-source-manifest.json`. It excludes
itself and its detached signature, avoiding the self-reference problem that
would result from putting a file's digest inside that same file.

This is stronger than hash comments scattered through source files:

- one verifier covers every tracked byte rather than selected languages;
- file deletion, insertion, rename, mode change, and content change alter the
  root;
- Git-index bytes stay stable across `core.autocrlf` checkout policies;
- one detached signature authenticates the entire set;
- verification works without trusting GitHub's view of the files.

## Threat boundary

A hash is not an authority. If GitHub is compromised, an attacker could replace
both a file and an unsigned hash file. The transferable trust root is therefore:

```text
offline Ed25519 private key
  -> detached signature over exact manifest bytes
  -> pinned public-key fingerprint stored outside GitHub
  -> Merkle root
  -> every tracked path, mode, kind, length, and SHA-256
```

The private key must remain outside the repository. The CLI rejects an in-repo
private-key path and creates only an AES-256-CBC-encrypted PKCS#8 key. The
passphrase is read from `SCBE_INTEGRITY_KEY_PASSPHRASE` and is never written to
the manifest or printed.

Committing a public key is convenient but is not enough by itself: a GitHub
attacker could replace that key too. Pin the `ed25519-sha256:...` fingerprint in
at least two independent places, such as the local Obsidian vault plus a printed
or offline removable-media copy.

## Commands

Node 24 executes these TypeScript files directly; no package install or network
access is required.

Generate from the staged Git index:

```powershell
node scripts/integrity/repository-integrity.ts generate
git add integrity/scbe-source-manifest.json
```

Verify a checkout against the Git index (safe with Windows CRLF conversion):

```powershell
node scripts/integrity/repository-integrity.ts verify --source git-index
```

Verify an extracted archive against its filesystem bytes:

```powershell
node scripts/integrity/repository-integrity.ts verify `
  --source filesystem `
  --allow-unverified-gitlinks
```

`--allow-unverified-gitlinks` is an explicit acknowledgement, not a successful
verification of submodule contents. Without it, archive verification fails
closed when the parent manifest contains a Git link.

Create an encrypted owner key outside the repository:

```powershell
$env:SCBE_INTEGRITY_KEY_PASSPHRASE = '<enter locally; do not paste into chat>'
node scripts/integrity/repository-integrity.ts keygen `
  --private-key C:\offline-scbe-keys\source-manifest-ed25519.pem `
  --public-key C:\offline-scbe-keys\source-manifest-ed25519.pub.pem
```

Sign and verify:

```powershell
node scripts/integrity/repository-integrity.ts sign `
  --private-key C:\offline-scbe-keys\source-manifest-ed25519.pem

node scripts/integrity/repository-integrity.ts verify-signature `
  --public-key C:\offline-scbe-keys\source-manifest-ed25519.pub.pem
```

Clear the passphrase environment variable after signing.

## Update contract

1. Stage exactly the intended source changes.
2. Run the narrow tests for those changes.
3. Generate the manifest from the index.
4. Stage the manifest and run Git-index verification.
5. Commit the source and manifest together.
6. Sign the committed manifest with the offline key.
7. Publish the detached signature and copy the manifest SHA-256, Merkle root,
   key fingerprint, commit ID, and signature SHA-256 to an authority outside
   GitHub.

The manifest contains no timestamp or branch name, so identical index state
produces identical bytes.

## What remains outside this slice

- The parent repository currently contains eleven Git links. Their exact commit
  IDs are locked by this manifest, but the referenced repository contents are
  not stored in the parent. Git bundles or verified mirrors are still required
  for a real GitHub-loss recovery kit.
- An offline owner key and detached production signature have not been created;
  doing so requires Issac to choose and retain a passphrase locally.
- GitHub branch rules, signed release tags, immutable release policy, artifact
  attestations, dependency review, and secret scanning are separate controls.
- A valid signature proves which bytes the owner signed. It does not prove the
  code is safe, complete, reproducible, or free of secrets.

## Evidence

- IMPLEMENTED: deterministic Git-index enumeration and streaming SHA-256.
- IMPLEMENTED: domain-separated RFC-6962-shaped Merkle root.
- IMPLEMENTED: strict schema, path, mode, summary, and root validation.
- IMPLEMENTED: Git-index and exact-filesystem verification.
- IMPLEMENTED: encrypted Ed25519 key generation and detached sign/verify.
- IMPLEMENTED: tests for determinism, tampering, extra files, Git links, wrong
  keys, wrong bytes, and in-repository private-key rejection.
- BLOCKED: production signature until the owner supplies a locally retained
  passphrase and chooses the external key location.
