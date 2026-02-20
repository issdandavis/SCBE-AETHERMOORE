/**
 * @file blackout-audit.ts
 * @module fleet/polly-pads/blackout-audit
 * @layer Layer 13, Layer 14
 * @component Blackout Merkle Audit Chain
 * @version 1.0.0
 *
 * During communications blackouts (Mars solar conjunction, orbital blackouts,
 * storm interference), the audit log switches to a Merkle Mountain Range (MMR)
 * structure for:
 *
 *   1. Fast append-only logging during blackout — O(1) amortized
 *   2. Efficient sync when comms resume — send peaks, not the full log
 *   3. Cryptographic proof that every action during blackout was validated
 *      by BFT quorum and fell within a signed Decision Envelope
 *
 * MMR Background:
 * A Merkle Mountain Range is an append-only authenticated data structure
 * composed of a series of perfect binary Merkle trees ("mountains"). When a
 * new leaf is appended, it merges with existing peaks of the same height,
 * producing internal nodes until no two peaks share the same height. The
 * result is a forest of decreasing-height trees whose roots ("peaks") can
 * be bagged into a single commitment hash.
 */

import { createHash } from 'crypto';
import { canonicalize } from '../../crypto/jcs.js';

// ═══════════════════════════════════════════════════════════════
// Types — Comms State
// ═══════════════════════════════════════════════════════════════

/** Communications state for the squad's link to ground control */
export type CommsState = 'LIVE' | 'DELAYED' | 'BLACKOUT';

// ═══════════════════════════════════════════════════════════════
// Types — MMR Leaf (BlackoutEvent)
// ═══════════════════════════════════════════════════════════════

/** A single leaf in the MMR — one governance event during blackout */
export interface BlackoutEvent {
  /** Monotonic sequence number within this blackout session */
  seq: number;
  /** Timestamp (ms since epoch) */
  timestamp: number;
  /** Unit that took the action */
  unitId: string;
  /** Action category that was evaluated */
  action: { id: string; domain: string; riskLevel: string };
  /** Decision made */
  decision: 'EXECUTE' | 'QUORUM_REQUIRED' | 'DENIED' | 'QUEUED';
  /** Envelope ID that authorized this (if any) */
  envelopeId: string | null;
  /** Quorum proof summary (votes/threshold) */
  quorumSummary?: { votes: number; threshold: number; agentIds: string[] };
  /** Resource state snapshot at decision time */
  resourceSnapshot?: Record<string, number>;
  /** Payload hash (what was the action's data) */
  payloadHash: string;
}

// ═══════════════════════════════════════════════════════════════
// Types — MMR Nodes
// ═══════════════════════════════════════════════════════════════

/** MMR node — either a leaf or an internal node */
export interface MMRNode {
  /** Node hash: leaf = sha256(event), internal = sha256(left || right) */
  hash: string;
  /** Height in the tree (0 = leaf) */
  height: number;
  /** Position in the MMR (0-indexed, append order) */
  position: number;
}

/** Inclusion proof for a specific event */
export interface MMRInclusionProof {
  /** The event's leaf index (0-indexed among leaves only) */
  leafIndex: number;
  /** Sibling hashes needed to reconstruct the peak */
  siblings: string[];
  /** Which peak this proof targets (index into the peaks array) */
  peakIndex: number;
  /** Current MMR size (total node count) when proof was generated */
  mmrSize: number;
}

// ═══════════════════════════════════════════════════════════════
// Types — Blackout Record (sync payload)
// ═══════════════════════════════════════════════════════════════

/** Complete blackout session record — sent to ground control on sync */
export interface BlackoutRecord {
  /** Session ID */
  sessionId: string;
  /** When blackout started (ms since epoch) */
  startedAt: number;
  /** When blackout ended (comms restored) */
  endedAt?: number;
  /** Total events logged */
  eventCount: number;
  /** MMR peaks (the roots of each mountain) */
  peaks: string[];
  /** Bagged peaks hash: sha256(peak0 || peak1 || ... || peakN) */
  baggedRoot: string;
  /** All events (for full sync) */
  events: BlackoutEvent[];
  /** Decision envelope IDs that were active during this blackout */
  envelopeIds: string[];
  /** Squad members during this blackout */
  squadMembers: string[];
}

// ═══════════════════════════════════════════════════════════════
// Hash Helpers
// ═══════════════════════════════════════════════════════════════

/**
 * Hash a BlackoutEvent to produce a leaf hash.
 *
 * Uses JCS (RFC 8785) canonicalization for deterministic serialization,
 * then SHA-256 for the digest — identical approach to voxelRecord.ts.
 *
 * @param event - The blackout event to hash
 * @returns Hex-encoded SHA-256 digest
 */
export function hashEvent(event: BlackoutEvent): string {
  const canonical = canonicalize(event);
  return createHash('sha256').update(canonical, 'utf-8').digest('hex');
}

/**
 * Hash two child nodes together to produce an internal MMR node hash.
 *
 * internal_hash = sha256(left_hash || right_hash)
 *
 * The hashes are concatenated as raw hex strings (not binary) for
 * simplicity and debuggability, consistent with the project's
 * existing hash-chain patterns (see ai_brain/audit.ts).
 *
 * @param left  - Hex hash of the left child
 * @param right - Hex hash of the right child
 * @returns Hex-encoded SHA-256 digest of the concatenation
 */
function hashInternal(left: string, right: string): string {
  return createHash('sha256').update(left + right, 'utf-8').digest('hex');
}

/**
 * Compute a bagged root from an array of peak hashes.
 *
 * baggedRoot = sha256(peak[0] || peak[1] || ... || peak[n-1])
 *
 * If there are no peaks (empty MMR), returns the hash of an empty string.
 *
 * @param peaks - Array of hex peak hashes, ordered left to right (tallest first)
 * @returns Hex-encoded SHA-256 digest
 */
function computeBaggedRoot(peaks: string[]): string {
  const combined = peaks.join('');
  return createHash('sha256').update(combined, 'utf-8').digest('hex');
}

// ═══════════════════════════════════════════════════════════════
// MMR Position Arithmetic
// ═══════════════════════════════════════════════════════════════
//
// An MMR assigns positions sequentially as nodes are appended.
// For n leaves, the total number of nodes follows a pattern tied
// to the binary representation of n.
//
// Key insight: the MMR is a forest of perfect binary trees. The
// heights of the trees correspond to the set bits in the binary
// representation of the leaf count.
//
// Example with 7 leaves (leafCount = 7 = binary 111 => peaks at heights 2, 1, 0):
//
//   Height 2:       6          (peak 0)
//                  / \
//   Height 1:    2     5       9          (peak 1)
//               / \   / \     / \
//   Height 0:  0   1 3   4   7   8   10   (peak 2)
//
//   Positions:  0  1  2  3  4  5  6  7  8  9  10
//   Leaves:     0  1     3  4        7  8      10
//   Leaf idx:   0  1     2  3        4  5       6
//
// The peaks after inserting n leaves are the roots of each
// perfect binary tree in the forest.

/**
 * Count the number of set bits (1-bits) in a non-negative integer.
 */
function popcount(n: number): number {
  let count = 0;
  let v = n;
  while (v > 0) {
    count += v & 1;
    v >>>= 1;
  }
  return count;
}

/**
 * Compute the total number of MMR nodes for a given number of leaves.
 *
 * totalNodes(n) = 2*n - popcount(n)
 *
 * This is because:
 * - n leaves contribute n nodes
 * - The number of internal nodes is n - popcount(n)
 *   (each merge reduces two trees to one; the number of merges
 *    when inserting n leaves equals n minus the number of remaining
 *    peaks, which is popcount(n))
 * - Total = n + (n - popcount(n)) = 2n - popcount(n)
 */
function totalMMRNodes(leafCount: number): number {
  return 2 * leafCount - popcount(leafCount);
}

/**
 * Given a leaf count, return the heights of the peaks in the MMR
 * (from tallest to shortest, i.e., from the most-significant set
 * bit to the least-significant set bit of leafCount).
 *
 * Each set bit at position k in the binary representation of
 * leafCount corresponds to a perfect binary tree of height k.
 */
function peakHeights(leafCount: number): number[] {
  const heights: number[] = [];
  let n = leafCount;
  let bit = 0;
  while (n > 0) {
    if (n & 1) {
      heights.push(bit);
    }
    n >>>= 1;
    bit++;
  }
  // Reverse so tallest (MSB) comes first
  return heights.reverse();
}

/**
 * Compute the MMR positions of the peaks for a given leaf count.
 *
 * We walk through the set bits of leafCount from MSB to LSB.
 * Each set bit at position k represents a perfect binary tree with
 * 2^k leaves and (2^(k+1) - 1) total nodes. The peak (root) of
 * that tree is at a specific MMR position.
 *
 * Returns an array of peak positions, tallest first.
 */
function peakPositions(leafCount: number): number[] {
  if (leafCount === 0) return [];

  const positions: number[] = [];
  const heights = peakHeights(leafCount);

  // Walk left to right through the peaks.
  // The first peak's root position is at (2^(h+1) - 2) where h is its height.
  // Each subsequent peak starts right after the previous peak's subtree.
  let pos = 0;
  for (const h of heights) {
    // A perfect binary tree of height h has (2^(h+1) - 1) nodes.
    const treeSize = (1 << (h + 1)) - 1;
    // The root of this tree is at position (pos + treeSize - 1)
    const peakPos = pos + treeSize - 1;
    positions.push(peakPos);
    // Next tree starts right after this one
    pos += treeSize;
  }

  return positions;
}

/**
 * Find which peak a given leaf index belongs to, and return:
 *  - peakIndex: which peak (0-based, in the peaks array)
 *  - localLeafIndex: the leaf's index within that peak's subtree
 *  - peakHeight: the height of that peak's tree
 *
 * We partition the leaves among the peaks: the first peak (height h0)
 * owns 2^h0 leaves, the next peak (height h1) owns 2^h1 leaves, etc.
 */
function locateLeafInPeaks(
  leafIndex: number,
  leafCount: number
): { peakIndex: number; localLeafIndex: number; peakHeight: number; peakStartPos: number } {
  const heights = peakHeights(leafCount);
  let cumulativeLeaves = 0;
  let pos = 0;

  for (let i = 0; i < heights.length; i++) {
    const h = heights[i];
    const leavesInPeak = 1 << h; // 2^h leaves in a tree of height h
    const treeSize = (1 << (h + 1)) - 1;

    if (leafIndex < cumulativeLeaves + leavesInPeak) {
      return {
        peakIndex: i,
        localLeafIndex: leafIndex - cumulativeLeaves,
        peakHeight: h,
        peakStartPos: pos,
      };
    }

    cumulativeLeaves += leavesInPeak;
    pos += treeSize;
  }

  throw new Error(`Leaf index ${leafIndex} out of range for ${leafCount} leaves`);
}

// ═══════════════════════════════════════════════════════════════
// MerkleAuditChain — MMR Implementation
// ═══════════════════════════════════════════════════════════════

/**
 * Merkle Mountain Range for blackout audit logging.
 *
 * An MMR is an append-only structure where:
 * - Leaves are hashed events
 * - Internal nodes are sha256(left || right)
 * - Multiple "peaks" (roots of complete binary trees) form the state
 * - The "bagged root" is sha256(all peaks concatenated)
 *
 * Properties:
 * - O(1) amortized append (worst case O(log n) when carries cascade)
 * - O(log n) inclusion proof generation
 * - O(peaks) sync — send peaks to verify integrity without full log
 *
 * @example
 * ```typescript
 * const chain = new MerkleAuditChain('session-001');
 * chain.append({
 *   timestamp: Date.now(),
 *   unitId: 'rover-alpha',
 *   action: { id: 'drill', domain: 'science', riskLevel: 'medium' },
 *   decision: 'EXECUTE',
 *   envelopeId: 'env-42',
 *   payloadHash: 'abc123...',
 * });
 *
 * const root = chain.getBaggedRoot();
 * const proof = chain.getInclusionProof(0);
 * const valid = MerkleAuditChain.verifyInclusion(
 *   chain.getEvents()[0], proof, chain.getPeaks().map(p => p.hash)
 * );
 * ```
 */
export class MerkleAuditChain {
  /** All MMR nodes in append order (leaves + internal nodes) */
  private nodes: MMRNode[] = [];

  /** All blackout events (leaves only) in sequence order */
  private events: BlackoutEvent[] = [];

  /** Unique session identifier */
  private sessionId: string;

  /** When this blackout session started */
  private startedAt: number;

  /** Decision envelope IDs encountered during this session */
  private envelopeIds: Set<string> = new Set();

  /** Squad members active during this session */
  private squadMembers: Set<string> = new Set();

  /** Next sequence number to assign */
  private seq: number = 0;

  /**
   * Create a new MerkleAuditChain.
   *
   * @param sessionId - Optional session identifier. If omitted, a
   *   random ID is generated from timestamp + random suffix.
   */
  constructor(sessionId?: string) {
    this.sessionId =
      sessionId ??
      `blackout-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 8)}`;
    this.startedAt = Date.now();
  }

  /**
   * Append a blackout event to the MMR.
   *
   * Assigns a monotonic sequence number, computes the leaf hash,
   * and performs any necessary merges with existing peaks of the
   * same height.
   *
   * @param event - The event to log (seq will be auto-assigned)
   * @returns The leaf index (0-based) of the appended event
   */
  append(event: Omit<BlackoutEvent, 'seq'>): number {
    // Assign sequence number
    const fullEvent: BlackoutEvent = { ...event, seq: this.seq };
    this.seq++;

    // Track metadata
    if (fullEvent.envelopeId) {
      this.envelopeIds.add(fullEvent.envelopeId);
    }
    this.squadMembers.add(fullEvent.unitId);

    // Store the event
    this.events.push(fullEvent);

    // Compute leaf hash and create the leaf node
    const leafHash = hashEvent(fullEvent);
    const leafPosition = this.nodes.length;
    const leafNode: MMRNode = {
      hash: leafHash,
      height: 0,
      position: leafPosition,
    };
    this.nodes.push(leafNode);

    // Merge with previous peaks of the same height.
    //
    // After appending a leaf, we check if the two most recent nodes
    // have the same height. If so, we merge them into an internal node
    // of height h+1. This process repeats (like binary carry propagation)
    // until no two consecutive peaks share a height.
    //
    // This is the core MMR invariant: the forest always has strictly
    // decreasing peak heights (when read left to right), mirroring the
    // set bits in the binary representation of the leaf count.
    while (this.nodes.length >= 2) {
      const top = this.nodes[this.nodes.length - 1];
      const prev = this.nodes[this.nodes.length - 2];

      if (top.height !== prev.height) break;

      // Merge: create internal node from prev (left) and top (right)
      const internalHash = hashInternal(prev.hash, top.hash);
      const internalNode: MMRNode = {
        hash: internalHash,
        height: top.height + 1,
        position: this.nodes.length,
      };
      this.nodes.push(internalNode);
    }

    // Return the leaf index
    return this.events.length - 1;
  }

  /**
   * Get the current peaks of the MMR.
   *
   * Peaks are the roots of each perfect binary tree in the forest.
   * For `n` leaves, the peak heights correspond to the set bits in
   * the binary representation of `n` (MSB to LSB). We compute each
   * peak's position in the nodes array from this structure.
   *
   * @returns Array of peak MMRNodes, tallest (leftmost) first
   */
  getPeaks(): MMRNode[] {
    const leafCount = this.events.length;
    if (leafCount === 0) return [];

    const positions = peakPositions(leafCount);
    return positions.map((pos) => this.nodes[pos]);
  }

  /**
   * Compute the bagged root hash.
   *
   * baggedRoot = sha256(peak0.hash || peak1.hash || ... || peakN.hash)
   *
   * This is the single commitment hash for the entire MMR state.
   *
   * @returns Hex-encoded SHA-256 digest of concatenated peak hashes
   */
  getBaggedRoot(): string {
    const peaks = this.getPeaks();
    return computeBaggedRoot(peaks.map((p) => p.hash));
  }

  /**
   * Generate an inclusion proof for a specific event by leaf index.
   *
   * The proof consists of sibling hashes along the path from the leaf
   * to its peak. A verifier can reconstruct the peak hash from the
   * event hash and the sibling hashes, then check that the peak
   * appears in the peaks array.
   *
   * @param leafIndex - 0-based index of the leaf (event) to prove
   * @returns Inclusion proof containing siblings and peak index
   * @throws Error if leafIndex is out of range
   */
  getInclusionProof(leafIndex: number): MMRInclusionProof {
    const leafCount = this.events.length;
    if (leafIndex < 0 || leafIndex >= leafCount) {
      throw new Error(`Leaf index ${leafIndex} out of range [0, ${leafCount})`);
    }

    const { peakIndex, localLeafIndex, peakHeight, peakStartPos } = locateLeafInPeaks(
      leafIndex,
      leafCount
    );

    // Navigate the perfect binary tree within this peak to collect siblings.
    //
    // Within a perfect binary tree of height h stored in an MMR region
    // starting at `peakStartPos`, the nodes are laid out in post-order.
    //
    // For a tree of height h:
    //   - Total nodes = 2^(h+1) - 1
    //   - Leaves are at positions computed by traversing left-to-right
    //
    // We navigate from the leaf up to the root, collecting the sibling
    // hash at each level.
    const siblings: string[] = [];

    if (peakHeight === 0) {
      // Single-leaf peak: no siblings needed
      return {
        leafIndex,
        siblings: [],
        peakIndex,
        mmrSize: this.nodes.length,
      };
    }

    // Navigate the perfect binary tree stored in post-order in the
    // nodes array, starting at peakStartPos.
    //
    // In a post-order perfect binary tree of height h:
    //   treeSize = 2^(h+1) - 1
    //   rootPos = peakStartPos + treeSize - 1
    //
    // To navigate, we track the current subtree's start position, height,
    // and which side (left/right) the target leaf is on.
    let subtreeStart = peakStartPos;
    let subtreeHeight = peakHeight;
    let targetLocalIndex = localLeafIndex;

    while (subtreeHeight > 0) {
      // The left subtree has height (subtreeHeight - 1) and size 2^subtreeHeight - 1
      const childTreeSize = (1 << subtreeHeight) - 1;
      const leftChildStart = subtreeStart;
      const leftChildRoot = leftChildStart + childTreeSize - 1;

      const rightChildStart = subtreeStart + childTreeSize;
      const rightChildRoot = rightChildStart + childTreeSize - 1;

      // The left subtree contains 2^(subtreeHeight-1) leaves
      const leftLeafCount = 1 << (subtreeHeight - 1);

      if (targetLocalIndex < leftLeafCount) {
        // Target is in the left subtree; sibling is the right subtree root
        siblings.push(this.nodes[rightChildRoot].hash);
        subtreeStart = leftChildStart;
      } else {
        // Target is in the right subtree; sibling is the left subtree root
        siblings.push(this.nodes[leftChildRoot].hash);
        subtreeStart = rightChildStart;
        targetLocalIndex -= leftLeafCount;
      }

      subtreeHeight--;
    }

    return {
      leafIndex,
      siblings,
      peakIndex,
      mmrSize: this.nodes.length,
    };
  }

  /**
   * Verify an inclusion proof against the given peaks.
   *
   * Reconstructs the peak hash from the event and sibling hashes,
   * then checks that it matches the specified peak.
   *
   * @param event  - The blackout event to verify
   * @param proof  - The inclusion proof
   * @param peaks  - Array of peak hashes (as returned by getPeaks)
   * @returns true if the proof is valid
   */
  static verifyInclusion(
    event: BlackoutEvent,
    proof: MMRInclusionProof,
    peaks: string[]
  ): boolean {
    if (proof.peakIndex < 0 || proof.peakIndex >= peaks.length) {
      return false;
    }

    // Recompute the leaf hash
    let currentHash = hashEvent(event);

    // The peak height equals the number of siblings in the proof
    // (one sibling per level from leaf to peak root).
    const peakHeight = proof.siblings.length;

    // Recover the total leaf count from the MMR node count.
    // This lets us reconstruct the peak structure and locate
    // the leaf's position within its peak's subtree.
    const leafCount = recoverLeafCount(proof.mmrSize);
    if (leafCount === null) {
      return false;
    }

    let location: ReturnType<typeof locateLeafInPeaks>;
    try {
      location = locateLeafInPeaks(proof.leafIndex, leafCount);
    } catch {
      return false;
    }

    if (location.peakIndex !== proof.peakIndex) {
      return false;
    }

    if (location.peakHeight !== peakHeight) {
      return false;
    }

    // Now walk up from the leaf, combining with siblings.
    // At each level, we need to know if the current node is a left or right child.
    // The local leaf index's bits (from MSB to LSB, peakHeight bits total)
    // encode the path: 0 = left, 1 = right.
    let localIndex = location.localLeafIndex;
    const pathBits: boolean[] = []; // true = right child, false = left child

    // Extract path bits from local leaf index (LSB to MSB, then reverse)
    for (let h = 0; h < peakHeight; h++) {
      pathBits.push((localIndex & 1) === 1);
      localIndex >>>= 1;
    }
    // pathBits[0] = deepest level, pathBits[peakHeight-1] = just below root

    // Walk up, combining with siblings
    for (let i = 0; i < peakHeight; i++) {
      const sibling = proof.siblings[i];
      if (pathBits[i]) {
        // Current node is right child: hash = sha256(sibling || current)
        currentHash = hashInternal(sibling, currentHash);
      } else {
        // Current node is left child: hash = sha256(current || sibling)
        currentHash = hashInternal(currentHash, sibling);
      }
    }

    // The reconstructed hash should match the peak
    return currentHash === peaks[proof.peakIndex];
  }

  /** Get the number of events (leaves) in the MMR */
  get size(): number {
    return this.events.length;
  }

  /** Get all events in sequence order */
  getEvents(): BlackoutEvent[] {
    return [...this.events];
  }

  /**
   * Get a specific event by its sequence number.
   *
   * @param seq - The monotonic sequence number
   * @returns The event, or undefined if not found
   */
  getEvent(seq: number): BlackoutEvent | undefined {
    return this.events.find((e) => e.seq === seq);
  }

  /**
   * Finalize the blackout session and produce a BlackoutRecord.
   *
   * Called when communications are restored. Seals the MMR state and
   * produces a record suitable for transmission to ground control.
   *
   * @returns A complete BlackoutRecord for sync
   */
  finalize(): BlackoutRecord {
    const peaks = this.getPeaks().map((p) => p.hash);
    const baggedRoot = computeBaggedRoot(peaks);

    return {
      sessionId: this.sessionId,
      startedAt: this.startedAt,
      endedAt: Date.now(),
      eventCount: this.events.length,
      peaks,
      baggedRoot,
      events: [...this.events],
      envelopeIds: Array.from(this.envelopeIds),
      squadMembers: Array.from(this.squadMembers),
    };
  }

  /**
   * Verify an entire BlackoutRecord.
   *
   * Ground control uses this to validate a complete blackout session.
   * Rebuilds the MMR from the events and checks that the resulting
   * peaks and bagged root match the record's claims.
   *
   * Checks performed:
   * 1. All events hash correctly to leaves
   * 2. All internal nodes hash correctly (via full MMR rebuild)
   * 3. Peaks match the record's peaks
   * 4. Bagged root matches the record's baggedRoot
   * 5. Events are in sequence order (seq 0, 1, 2, ...)
   * 6. No gaps in sequence numbers
   * 7. Event count matches events array length
   *
   * @param record - The BlackoutRecord to verify
   * @returns Object with `valid` boolean and array of error descriptions
   */
  static verifyRecord(record: BlackoutRecord): { valid: boolean; errors: string[] } {
    const errors: string[] = [];

    // Check 7: eventCount matches actual events
    if (record.eventCount !== record.events.length) {
      errors.push(
        `Event count mismatch: claimed ${record.eventCount}, actual ${record.events.length}`
      );
    }

    // Check 5 & 6: sequence order and no gaps
    for (let i = 0; i < record.events.length; i++) {
      if (record.events[i].seq !== i) {
        errors.push(
          `Sequence gap/disorder at index ${i}: expected seq=${i}, got seq=${record.events[i].seq}`
        );
      }
    }

    // Rebuild the MMR from scratch to verify hashes (Checks 1, 2, 3, 4)
    const rebuild = new MerkleAuditChain(record.sessionId);
    for (const event of record.events) {
      // Strip seq and re-append (seq is auto-assigned)
      const { seq: _seq, ...rest } = event;
      rebuild.append(rest);
    }

    // Check 3: peaks match
    const rebuiltPeaks = rebuild.getPeaks().map((p) => p.hash);
    if (rebuiltPeaks.length !== record.peaks.length) {
      errors.push(
        `Peak count mismatch: claimed ${record.peaks.length}, rebuilt ${rebuiltPeaks.length}`
      );
    } else {
      for (let i = 0; i < rebuiltPeaks.length; i++) {
        if (rebuiltPeaks[i] !== record.peaks[i]) {
          errors.push(`Peak ${i} mismatch: claimed ${record.peaks[i]}, rebuilt ${rebuiltPeaks[i]}`);
        }
      }
    }

    // Check 4: bagged root matches
    const rebuiltBaggedRoot = rebuild.getBaggedRoot();
    if (rebuiltBaggedRoot !== record.baggedRoot) {
      errors.push(
        `Bagged root mismatch: claimed ${record.baggedRoot}, rebuilt ${rebuiltBaggedRoot}`
      );
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  }
}

// ═══════════════════════════════════════════════════════════════
// Helper: Recover leaf count from MMR node count
// ═══════════════════════════════════════════════════════════════

/**
 * Recover the number of leaves from the total MMR node count.
 *
 * Given totalNodes = 2*n - popcount(n), solve for n.
 *
 * Since popcount(n) <= log2(n) + 1, we know n is close to
 * totalNodes / 2. We search in a small range.
 *
 * @param mmrSize - Total number of nodes in the MMR
 * @returns The leaf count, or null if mmrSize is not a valid MMR size
 */
function recoverLeafCount(mmrSize: number): number | null {
  if (mmrSize === 0) return 0;

  // n is approximately mmrSize / 2, but slightly more due to popcount subtraction
  // Search in range [mmrSize/2, mmrSize]
  const lo = Math.floor(mmrSize / 2);
  const hi = mmrSize;

  for (let n = lo; n <= hi; n++) {
    if (totalMMRNodes(n) === mmrSize) {
      return n;
    }
  }

  return null;
}

// ═══════════════════════════════════════════════════════════════
// BlackoutManager — integrates with ClosedNetwork
// ═══════════════════════════════════════════════════════════════

/**
 * Manages blackout sessions for a squad.
 *
 * Integrates with ClosedNetwork to detect comms state changes and
 * maintains a timeline of blackout sessions with their MMR audit chains.
 *
 * Usage lifecycle:
 *   1. enterBlackout() — comms lost, start a new MMR chain
 *   2. logEvent() — each governance decision during blackout is appended
 *   3. exitBlackout() — comms restored, finalize and store the record
 *   4. getCompletedSessions() — ground control retrieves records for sync
 *   5. clearSyncedSessions() — after ground confirms receipt, purge local
 *
 * @example
 * ```typescript
 * const mgr = new BlackoutManager();
 *
 * // Solar conjunction begins
 * const sessionId = mgr.enterBlackout(
 *   ['rover-1', 'rover-2', 'drone-1'],
 *   ['env-042', 'env-043']
 * );
 *
 * // Log governance events during blackout
 * mgr.logEvent({
 *   timestamp: Date.now(),
 *   unitId: 'rover-1',
 *   action: { id: 'sample-drill', domain: 'science', riskLevel: 'medium' },
 *   decision: 'EXECUTE',
 *   envelopeId: 'env-042',
 *   payloadHash: '0xdead...',
 * });
 *
 * // Conjunction ends
 * const record = mgr.exitBlackout();
 * // => Send record to ground control
 * ```
 */
export class BlackoutManager {
  /** The currently active MMR chain (null if not in blackout) */
  private activeChain: MerkleAuditChain | null = null;

  /** Completed blackout session records awaiting ground sync */
  private completedSessions: BlackoutRecord[] = [];

  /** Current communications state */
  private commsState: CommsState = 'LIVE';

  /** Running total of all events logged across all sessions */
  private totalEventsLogged: number = 0;

  constructor() {
    // Initialized in LIVE state with no active chain
  }

  /**
   * Start a blackout session.
   *
   * Transitions to BLACKOUT state and creates a new MerkleAuditChain.
   * All subsequent logEvent() calls are appended to this chain until
   * exitBlackout() is called.
   *
   * @param squadMembers      - IDs of squad members active during this blackout
   * @param activeEnvelopeIds - Decision envelope IDs that are valid during this blackout
   * @returns The session ID for the new blackout chain
   * @throws Error if already in a blackout session
   */
  enterBlackout(squadMembers: string[], activeEnvelopeIds: string[]): string {
    if (this.activeChain !== null) {
      throw new Error('Already in a blackout session — call exitBlackout() first');
    }

    this.commsState = 'BLACKOUT';

    const sessionId = `blackout-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 8)}`;
    this.activeChain = new MerkleAuditChain(sessionId);

    // Store pre-declared envelope IDs and squad members. These will be
    // merged with any IDs discovered from events at finalize time, ensuring
    // the BlackoutRecord captures both the initial roster and any units
    // that joined during the blackout.
    this._pendingEnvelopeIds = new Set(activeEnvelopeIds);
    this._pendingSquadMembers = new Set(squadMembers);

    return sessionId;
  }

  /** Envelope IDs declared at enterBlackout (merged with event-derived IDs at finalize) */
  private _pendingEnvelopeIds: Set<string> = new Set();

  /** Squad members declared at enterBlackout (merged with event-derived members at finalize) */
  private _pendingSquadMembers: Set<string> = new Set();

  /**
   * Log a governance event during an active blackout.
   *
   * @param event - The event to log (seq is auto-assigned by the chain)
   * @returns The sequence number assigned to this event
   * @throws Error if not currently in a blackout session
   */
  logEvent(event: Omit<BlackoutEvent, 'seq'>): number {
    if (this.activeChain === null) {
      throw new Error('Not in a blackout session — call enterBlackout() first');
    }

    const leafIndex = this.activeChain.append(event);
    this.totalEventsLogged++;
    return leafIndex;
  }

  /**
   * End the blackout and finalize the chain.
   *
   * Transitions back to LIVE state, finalizes the MerkleAuditChain
   * into a BlackoutRecord, and stores it for later ground sync.
   *
   * @returns The finalized BlackoutRecord, or null if no session was active
   */
  exitBlackout(): BlackoutRecord | null {
    if (this.activeChain === null) {
      return null;
    }

    this.commsState = 'LIVE';

    const record = this.activeChain.finalize();

    // Merge pre-declared envelope IDs and squad members with
    // those discovered from events
    const mergedEnvelopeIds = new Set([
      ...record.envelopeIds,
      ...this._pendingEnvelopeIds,
    ]);
    const mergedSquadMembers = new Set([
      ...record.squadMembers,
      ...this._pendingSquadMembers,
    ]);

    record.envelopeIds = Array.from(mergedEnvelopeIds);
    record.squadMembers = Array.from(mergedSquadMembers);

    this.completedSessions.push(record);
    this.activeChain = null;
    this._pendingEnvelopeIds.clear();
    this._pendingSquadMembers.clear();

    return record;
  }

  /**
   * Get the current communications state.
   *
   * @returns 'LIVE', 'DELAYED', or 'BLACKOUT'
   */
  getCommsState(): CommsState {
    return this.commsState;
  }

  /**
   * Check if currently in a blackout session.
   *
   * @returns true if a blackout session is active
   */
  isBlackout(): boolean {
    return this.activeChain !== null;
  }

  /**
   * Get all completed session records awaiting ground sync.
   *
   * @returns Array of BlackoutRecords
   */
  getCompletedSessions(): BlackoutRecord[] {
    return [...this.completedSessions];
  }

  /**
   * Clear synced sessions after ground control confirms receipt.
   *
   * @param sessionIds - The session IDs to remove from local storage
   */
  clearSyncedSessions(sessionIds: string[]): void {
    const idSet = new Set(sessionIds);
    this.completedSessions = this.completedSessions.filter(
      (s) => !idSet.has(s.sessionId)
    );
  }

  /**
   * Get the active chain's current bagged root.
   *
   * Useful for including in heartbeat/status messages so that
   * even during blackout, the current integrity commitment is
   * available for local mesh broadcast.
   *
   * @returns Hex-encoded bagged root, or null if no active session
   */
  getCurrentRoot(): string | null {
    if (this.activeChain === null) return null;
    return this.activeChain.getBaggedRoot();
  }

  /**
   * Get operational statistics.
   *
   * @returns Stats object with session and event counts
   */
  getStats(): {
    isBlackout: boolean;
    currentSessionEvents: number;
    completedSessions: number;
    totalEventsLogged: number;
  } {
    return {
      isBlackout: this.activeChain !== null,
      currentSessionEvents: this.activeChain?.size ?? 0,
      completedSessions: this.completedSessions.length,
      totalEventsLogged: this.totalEventsLogged,
    };
  }
}
