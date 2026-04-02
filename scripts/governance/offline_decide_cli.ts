import { createImmutableLaws } from '../../src/governance/immutable_laws';
import {
  AuditLedger,
  DECIDE,
  PQCrypto,
  type EnforcementRequest,
  type FluxManifest,
  type GovernanceScalars,
  type OfflineRuntime,
} from '../../src/governance/offline_mode';

interface CliInput {
  action?: string;
  subject?: string;
  object?: string;
  payload_hash_hex: string;
  scalars: Omit<GovernanceScalars, 'trust_level'>;
  manifest_stale?: boolean;
}

function toHex(bytes: Uint8Array): string {
  return Buffer.from(bytes).toString('hex');
}

function fromHex(hex: string): Uint8Array {
  return new Uint8Array(Buffer.from(hex, 'hex'));
}

function canonicalStringify(value: unknown): string {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map((v) => canonicalStringify(v)).join(',')}]`;
  const record = value as Record<string, unknown>;
  const keys = Object.keys(record).sort();
  const entries = keys.map((key) => `${JSON.stringify(key)}:${canonicalStringify(record[key])}`);
  return `{${entries.join(',')}}`;
}

function canonicalManifestBytes(
  manifest: Omit<FluxManifest, 'signature'>
): Uint8Array {
  return new TextEncoder().encode(
    canonicalStringify({
      manifest_id: manifest.manifest_id,
      epoch_id: manifest.epoch_id,
      valid_from: manifest.valid_from.toString(),
      valid_until: manifest.valid_until.toString(),
      policy_weights: manifest.policy_weights,
      thresholds: manifest.thresholds,
      curvature_params: manifest.curvature_params,
      required_keys: manifest.required_keys,
    })
  );
}

async function readStdin(): Promise<string> {
  const chunks: Buffer[] = [];
  for await (const chunk of process.stdin) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }
  return Buffer.concat(chunks).toString('utf8').trim();
}

async function main(): Promise<void> {
  const raw = await readStdin();
  if (!raw) {
    throw new Error('Expected JSON payload on stdin');
  }

  const input = JSON.parse(raw) as CliInput;
  const payloadHash = fromHex(input.payload_hash_hex);

  const sigKeys = PQCrypto.generateSigningKeys();
  const kemKeys = PQCrypto.generateKEMKeys();
  const laws = createImmutableLaws({
    metric_signature: 'harmonic_v3',
    tongues_set: ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'],
    geometry_model: 'poincare_ball',
    layer_behaviors: { 12: 'harmonic_scale' },
  });

  const manifestBase: Omit<FluxManifest, 'signature'> = {
    manifest_id: 'governance-gated-agent-loop',
    epoch_id: '1',
    valid_from: 0n,
    valid_until: input.manifest_stale ? 0n : 999999999n,
    policy_weights: {},
    thresholds: {},
    curvature_params: {},
    required_keys: [],
  };

  const manifest: FluxManifest = {
    ...manifestBase,
    signature: PQCrypto.sign(sigKeys.secretKey, canonicalManifestBytes(manifestBase)),
  };

  const request: EnforcementRequest = {
    action: input.action ?? 'code.patch.proposal',
    subject: input.subject ?? 'governance-gated-agent',
    object: input.object ?? 'candidate',
    payload_hash: payloadHash,
  };

  const runtime: OfflineRuntime = {
    laws,
    manifest,
    keys: {
      signing_secret: sigKeys.secretKey,
      signing_public: sigKeys.publicKey,
      kem_secret: kemKeys.secretKey,
      kem_public: kemKeys.publicKey,
      fingerprints: [PQCrypto.fingerprint(sigKeys.publicKey)],
    },
    ledger: new AuditLedger(sigKeys.secretKey),
    voxelRoot: PQCrypto.hash(payloadHash),
    nowMono: 100n,
    signerPubKey: sigKeys.publicKey,
    computeMMX: () => ({ ...input.scalars }),
  };

  const result = DECIDE(request, runtime);

  process.stdout.write(
    JSON.stringify(
      {
        decision: result.decision,
        reason_codes: result.reason_codes,
        governance_scalars: result.governance_scalars,
        proof: {
          decision: result.proof.decision,
          reason_codes: result.proof.reason_codes,
          timestamp_monotonic: result.proof.timestamp_monotonic.toString(),
          inputs_hash_hex: toHex(result.proof.inputs_hash),
          laws_hash_hex: toHex(result.proof.laws_hash),
          manifest_hash_hex: toHex(result.proof.manifest_hash),
          state_root_hex: toHex(result.proof.state_root),
          signature_hex: toHex(result.proof.signature),
        },
      },
      null,
      2
    )
  );
}

main().catch((error) => {
  process.stderr.write(`${error instanceof Error ? error.stack ?? error.message : String(error)}\n`);
  process.exit(1);
});
