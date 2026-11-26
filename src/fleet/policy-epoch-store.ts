/**
 * Durable policy-epoch high-water storage for NodeKernel.
 *
 * This closes process-restart rollback: a new kernel instance reloads the
 * largest epoch accepted for its node and rejects older signed manifests.
 * The file record is HMAC-authenticated, guarded against concurrent writers,
 * and replaced atomically. A host-level attacker able to roll back the entire
 * directory can still restore an older valid record; deployments requiring
 * that stronger property must anchor this interface in a TPM monotonic counter
 * or remote append-only authority.
 */

import {
  closeSync,
  existsSync,
  fsyncSync,
  mkdirSync,
  openSync,
  readFileSync,
  renameSync,
  unlinkSync,
  writeFileSync,
} from 'fs';
import { basename, join, resolve } from 'path';
import { createHash, createHmac, randomBytes, timingSafeEqual } from 'crypto';

export interface PolicyEpochStore {
  /** Return the durable maximum accepted epoch, or zero for a new node. */
  loadMaxEpoch(nodeId: string): number;
  /** Atomically advance the durable maximum. Regressions must be rejected. */
  advanceMaxEpoch(nodeId: string, epoch: number): void;
}

interface PolicyEpochRecord {
  schema: 'scbe.policy-epoch.v1';
  nodeId: string;
  maxEpoch: number;
  updatedAt: number;
  mac: string;
}

function validateNodeId(nodeId: string): void {
  if (!nodeId || nodeId.length > 512) {
    throw new Error('Policy epoch nodeId must contain 1..512 characters');
  }
}

function validateEpoch(epoch: number, allowZero: boolean = false): void {
  const minimum = allowZero ? 0 : 1;
  if (!Number.isSafeInteger(epoch) || epoch < minimum) {
    throw new Error(`Policy epoch must be a safe integer >= ${minimum}`);
  }
}

/**
 * HMAC-authenticated local file store with atomic replacement.
 *
 * Use a dedicated integrity key with at least 32 random bytes. The key is not
 * written to disk by this class.
 */
export class HmacFilePolicyEpochStore implements PolicyEpochStore {
  private readonly directory: string;
  private readonly integrityKey: Buffer;

  constructor(directory: string, integrityKey: Buffer | string) {
    if (!directory) throw new Error('Policy epoch store directory is required');
    this.directory = resolve(directory);
    this.integrityKey =
      typeof integrityKey === 'string'
        ? Buffer.from(integrityKey, 'utf8')
        : Buffer.from(integrityKey);
    if (this.integrityKey.length < 32) {
      throw new Error('Policy epoch integrity key must be at least 32 bytes');
    }
  }

  public loadMaxEpoch(nodeId: string): number {
    validateNodeId(nodeId);
    const path = this.recordPath(nodeId);
    if (!existsSync(path)) return 0;

    let parsed: unknown;
    try {
      parsed = JSON.parse(readFileSync(path, 'utf8'));
    } catch {
      throw new Error('Policy epoch record is unreadable');
    }

    if (!this.isRecord(parsed) || parsed.nodeId !== nodeId) {
      throw new Error('Policy epoch record has invalid schema or node binding');
    }
    validateEpoch(parsed.maxEpoch, true);

    const expected = this.macFor(parsed);
    const supplied = Buffer.from(parsed.mac, 'hex');
    if (supplied.length !== expected.length || !timingSafeEqual(supplied, expected)) {
      throw new Error('Policy epoch record integrity check failed');
    }
    return parsed.maxEpoch;
  }

  public advanceMaxEpoch(nodeId: string, epoch: number): void {
    validateNodeId(nodeId);
    validateEpoch(epoch);
    mkdirSync(this.directory, { recursive: true });
    const target = this.recordPath(nodeId);
    const lockPath = `${target}.lock`;
    let lockFd: number | null = null;
    try {
      try {
        // A leftover lock fails closed. Operators may remove it only after
        // verifying no writer is alive; automatic stale-lock breaking would
        // reintroduce the race this guard is meant to close.
        lockFd = openSync(lockPath, 'wx', 0o600);
      } catch {
        throw new Error('Policy epoch store is locked; refusing concurrent update');
      }

      const current = this.loadMaxEpoch(nodeId);
      if (epoch <= current) {
        throw new Error(`Policy epoch regression:${epoch}<=${current}`);
      }

      const unsigned = {
        schema: 'scbe.policy-epoch.v1' as const,
        nodeId,
        maxEpoch: epoch,
        updatedAt: Date.now(),
      };
      const record: PolicyEpochRecord = {
        ...unsigned,
        mac: this.macFor(unsigned).toString('hex'),
      };

      const temp = join(
        this.directory,
        `.${basename(target)}.${process.pid}.${randomBytes(6).toString('hex')}.tmp`
      );
      let tempFd: number | null = null;
      try {
        writeFileSync(temp, `${JSON.stringify(record)}\n`, {
          encoding: 'utf8',
          flag: 'wx',
          mode: 0o600,
        });
        // Windows requires a writable handle for fsync in some Node builds.
        tempFd = openSync(temp, 'r+');
        fsyncSync(tempFd);
        closeSync(tempFd);
        tempFd = null;
        renameSync(temp, target);
      } finally {
        if (tempFd !== null) closeSync(tempFd);
        if (existsSync(temp)) unlinkSync(temp);
      }
    } finally {
      if (lockFd !== null) {
        closeSync(lockFd);
        if (existsSync(lockPath)) unlinkSync(lockPath);
      }
    }
  }

  private recordPath(nodeId: string): string {
    const digest = createHash('sha256').update(nodeId, 'utf8').digest('hex');
    return join(this.directory, `${digest}.json`);
  }

  private macFor(record: Omit<PolicyEpochRecord, 'mac'>): Buffer {
    const canonical = JSON.stringify({
      schema: record.schema,
      nodeId: record.nodeId,
      maxEpoch: record.maxEpoch,
      updatedAt: record.updatedAt,
    });
    return createHmac('sha256', this.integrityKey).update(canonical).digest();
  }

  private isRecord(value: unknown): value is PolicyEpochRecord {
    if (!value || typeof value !== 'object') return false;
    const candidate = value as Partial<PolicyEpochRecord>;
    return (
      candidate.schema === 'scbe.policy-epoch.v1' &&
      typeof candidate.nodeId === 'string' &&
      typeof candidate.maxEpoch === 'number' &&
      typeof candidate.updatedAt === 'number' &&
      typeof candidate.mac === 'string' &&
      /^[0-9a-f]{64}$/i.test(candidate.mac)
    );
  }
}
