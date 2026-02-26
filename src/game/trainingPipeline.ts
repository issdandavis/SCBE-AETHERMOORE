/**
 * @file trainingPipeline.ts
 * @module game/trainingPipeline
 * @layer Layer 12, Layer 13, Layer 14
 * @component Training Pipeline — Game Events → SFT → HuggingFace Fine-Tune
 *
 * How it works:
 *
 *   1. Player PAYS Energy Tokens for an adventure (dungeon run, tower floor, etc.)
 *   2. During the adventure, game events stream into a 3-tier dataset:
 *        RAW → QUARANTINED → APPROVED
 *   3. Approved events are formatted as SFT (Supervised Fine-Tune) pairs:
 *        { instruction: <game_context>, response: <companion_action> }
 *   4. SFT pairs are batched and pushed to HuggingFace dataset repo.
 *   5. When enough data accumulates, a fine-tune job trains the companion model.
 *   6. The updated model weights deploy back into the companion's AI.
 *
 * This means: every adventure the player pays for TRAINS their companion.
 * The companion literally learns from the player's gameplay decisions.
 *
 * A3: Causality — events are time-ordered, append-only.
 * A5: Composition — full audit trail from payment → events → SFT → model.
 */

import { ConsumptionRecord } from './energyToken.js';

// ---------------------------------------------------------------------------
//  Event Types — What happens during an adventure
// ---------------------------------------------------------------------------

/** Categories of game events that generate training data */
export type GameEventType =
  | 'combat_action'       // Player chose an attack / defense / dodge
  | 'companion_command'   // Player issued a companion command
  | 'companion_response'  // Companion autonomous behavior
  | 'evolution_choice'    // Player selected an evolution branch
  | 'formation_change'    // Player rearranged fleet formation
  | 'codex_query'         // Player used codex terminal
  | 'npc_dialogue'        // Player made a dialogue choice
  | 'item_use'            // Player used an item
  | 'exploration_action'  // Player explored / solved puzzle
  | 'tower_strategy';     // Tower floor tactical decision

/** A single game event captured during an adventure */
export interface GameEvent {
  readonly eventId: string;
  readonly sessionId: string;
  readonly playerId: string;
  readonly companionId: string;
  readonly eventType: GameEventType;
  readonly timestamp: number;

  /** The game state context BEFORE the event */
  readonly context: EventContext;

  /** The action that was taken */
  readonly action: EventAction;

  /** The outcome that resulted */
  readonly outcome: EventOutcome;
}

/** Snapshot of game state at the moment of the event */
export interface EventContext {
  /** Current tongue vector (6D) */
  readonly tongueVector: readonly number[];
  /** Current floor / area */
  readonly location: string;
  /** Companion's current HP ratio (0-1) */
  readonly companionHpRatio: number;
  /** Number of enemies present */
  readonly enemyCount: number;
  /** Current formation type */
  readonly formationType: string;
  /** Bond level with companion */
  readonly bondLevel: number;
  /** Companion evolution stage */
  readonly evolutionStage: string;
  /** Any active status effects */
  readonly statusEffects: readonly string[];
}

/** What action was taken */
export interface EventAction {
  /** Action identifier */
  readonly actionId: string;
  /** Human-readable description */
  readonly description: string;
  /** Whether this was a player choice or companion autonomous */
  readonly source: 'player' | 'companion' | 'system';
  /** Confidence of companion action (0-1, only for companion source) */
  readonly confidence: number;
}

/** What happened as a result */
export interface EventOutcome {
  /** Was it successful? */
  readonly success: boolean;
  /** Damage dealt / healed / etc */
  readonly numericResult: number;
  /** Text description */
  readonly description: string;
  /** Any tongue vector changes */
  readonly tongueShift: readonly number[] | null;
  /** SCBE safety score for this event */
  readonly safetyScore: number;
}

// ---------------------------------------------------------------------------
//  3-Tier Dataset — RAW → QUARANTINED → APPROVED
// ---------------------------------------------------------------------------

/** Dataset tiers — events must be promoted through each tier */
export type DatasetTier = 'RAW' | 'QUARANTINED' | 'APPROVED';

/** A dataset record wrapping a game event with tier metadata */
export interface DatasetRecord {
  readonly recordId: string;
  readonly event: GameEvent;
  tier: DatasetTier;
  readonly createdAt: number;
  promotedAt: number | null;
  /** Why it was quarantined (if applicable) */
  quarantineReason: string | null;
  /** Review notes */
  reviewNotes: string | null;
}

// ---------------------------------------------------------------------------
//  SFT Pair — The actual training data format
// ---------------------------------------------------------------------------

/** An SFT (Supervised Fine-Tuning) pair derived from approved events */
export interface SFTPair {
  readonly pairId: string;
  readonly sourceRecordId: string;
  readonly companionId: string;

  /** The instruction / prompt for the model */
  readonly instruction: string;

  /** The expected response (what the companion should learn to do) */
  readonly response: string;

  /** Category for dataset organization */
  readonly category: string;

  /** Quality score (0-1) based on outcome success and safety */
  readonly qualityScore: number;

  readonly timestamp: number;
}

/** HuggingFace push batch */
export interface HFBatch {
  readonly batchId: string;
  readonly companionId: string;
  readonly pairs: readonly SFTPair[];
  readonly datasetRepo: string;
  readonly pushedAt: number | null;
  readonly status: 'pending' | 'pushed' | 'failed';
}

/** Fine-tune job tracking */
export interface FineTuneJob {
  readonly jobId: string;
  readonly companionId: string;
  readonly datasetRepo: string;
  readonly modelRepo: string;
  readonly batchIds: readonly string[];
  readonly totalPairs: number;
  readonly startedAt: number;
  completedAt: number | null;
  status: 'queued' | 'running' | 'completed' | 'failed';
  /** Model checkpoint hash when complete */
  checkpointHash: string | null;
}

// ---------------------------------------------------------------------------
//  Safety Thresholds
// ---------------------------------------------------------------------------

/** Minimum SCBE safety score to auto-approve an event */
export const AUTO_APPROVE_THRESHOLD = 0.8;

/** Below this score, event goes to QUARANTINED instead of APPROVED */
export const QUARANTINE_THRESHOLD = 0.4;

/** Minimum quality score for an SFT pair to be included in training */
export const MIN_QUALITY_SCORE = 0.5;

/** Number of approved pairs needed before triggering a fine-tune */
export const FINE_TUNE_THRESHOLD = 100;

// ---------------------------------------------------------------------------
//  Training Pipeline
// ---------------------------------------------------------------------------

export class TrainingPipeline {
  private _companionId: string;
  private _playerId: string;
  private _records: DatasetRecord[] = [];
  private _pairs: SFTPair[] = [];
  private _batches: HFBatch[] = [];
  private _jobs: FineTuneJob[] = [];
  private _datasetRepo: string;
  private _modelRepo: string;

  constructor(
    companionId: string,
    playerId: string,
    datasetRepo: string = '',
    modelRepo: string = ''
  ) {
    this._companionId = companionId;
    this._playerId = playerId;
    this._datasetRepo = datasetRepo || `scbe-companion-${companionId}`;
    this._modelRepo = modelRepo || `scbe-model-${companionId}`;
  }

  get companionId(): string {
    return this._companionId;
  }

  get datasetRepo(): string {
    return this._datasetRepo;
  }

  get modelRepo(): string {
    return this._modelRepo;
  }

  // -------------------------------------------------------------------------
  //  Tier 1: Ingest — RAW events
  // -------------------------------------------------------------------------

  /**
   * Ingest a game event into the RAW tier.
   * Returns the dataset record ID.
   */
  ingestEvent(event: GameEvent): string {
    const recordId = `rec_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;

    const record: DatasetRecord = {
      recordId,
      event,
      tier: 'RAW',
      createdAt: Date.now() / 1000,
      promotedAt: null,
      quarantineReason: null,
      reviewNotes: null,
    };

    this._records.push(record);
    return recordId;
  }

  /**
   * Bulk-ingest events from an adventure session.
   * Automatically classifies into QUARANTINED or APPROVED based on safety score.
   */
  ingestSession(events: GameEvent[]): { approved: number; quarantined: number; rejected: number } {
    let approved = 0;
    let quarantined = 0;
    let rejected = 0;

    for (const event of events) {
      const recordId = this.ingestEvent(event);
      const result = this.classifyRecord(recordId);

      if (result === 'APPROVED') approved++;
      else if (result === 'QUARANTINED') quarantined++;
      else rejected++;
    }

    return { approved, quarantined, rejected };
  }

  // -------------------------------------------------------------------------
  //  Tier 2: Classify — RAW → QUARANTINED or APPROVED
  // -------------------------------------------------------------------------

  /**
   * Classify a RAW record based on its safety score.
   * High safety = auto-approve. Low safety = quarantine. Very low = reject.
   */
  classifyRecord(recordId: string): DatasetTier | 'REJECTED' {
    const record = this._records.find((r) => r.recordId === recordId);
    if (!record || record.tier !== 'RAW') return 'REJECTED';

    const safetyScore = record.event.outcome.safetyScore;

    if (safetyScore >= AUTO_APPROVE_THRESHOLD) {
      record.tier = 'APPROVED';
      record.promotedAt = Date.now() / 1000;
      return 'APPROVED';
    } else if (safetyScore >= QUARANTINE_THRESHOLD) {
      record.tier = 'QUARANTINED';
      record.quarantineReason = `Safety score ${safetyScore.toFixed(2)} below auto-approve threshold`;
      return 'QUARANTINED';
    } else {
      // Very low safety — remove from pipeline
      this._records = this._records.filter((r) => r.recordId !== recordId);
      return 'REJECTED';
    }
  }

  /**
   * Manually approve a quarantined record (human review).
   */
  approveRecord(recordId: string, reviewNotes: string = ''): boolean {
    const record = this._records.find((r) => r.recordId === recordId);
    if (!record || record.tier !== 'QUARANTINED') return false;

    record.tier = 'APPROVED';
    record.promotedAt = Date.now() / 1000;
    record.reviewNotes = reviewNotes;
    return true;
  }

  /**
   * Reject a quarantined record (human review).
   */
  rejectRecord(recordId: string, reason: string = ''): boolean {
    const record = this._records.find((r) => r.recordId === recordId);
    if (!record || record.tier !== 'QUARANTINED') return false;

    this._records = this._records.filter((r) => r.recordId !== recordId);
    return true;
  }

  // -------------------------------------------------------------------------
  //  Tier 3: Generate SFT Pairs — APPROVED → SFT
  // -------------------------------------------------------------------------

  /**
   * Generate SFT pairs from all approved records that haven't been processed.
   * Returns the number of new pairs generated.
   */
  generateSFTPairs(): number {
    const approved = this._records.filter((r) => r.tier === 'APPROVED');
    const existingSourceIds = new Set(this._pairs.map((p) => p.sourceRecordId));

    let count = 0;
    for (const record of approved) {
      if (existingSourceIds.has(record.recordId)) continue;

      const pair = this._eventToSFTPair(record);
      if (pair && pair.qualityScore >= MIN_QUALITY_SCORE) {
        this._pairs.push(pair);
        count++;
      }
    }

    return count;
  }

  /**
   * Convert a dataset record into an SFT instruction/response pair.
   */
  private _eventToSFTPair(record: DatasetRecord): SFTPair | null {
    const event = record.event;
    const ctx = event.context;
    const action = event.action;
    const outcome = event.outcome;

    // Build the instruction (context prompt)
    const instruction = [
      `[${event.eventType.toUpperCase()}]`,
      `Location: ${ctx.location}`,
      `Companion HP: ${(ctx.companionHpRatio * 100).toFixed(0)}%`,
      `Bond Level: ${ctx.bondLevel}`,
      `Evolution: ${ctx.evolutionStage}`,
      `Formation: ${ctx.formationType}`,
      `Enemies: ${ctx.enemyCount}`,
      ctx.statusEffects.length > 0
        ? `Status: ${ctx.statusEffects.join(', ')}`
        : null,
      `Tongue: [${ctx.tongueVector.map((v) => v.toFixed(2)).join(', ')}]`,
      ``,
      `What action should the companion take?`,
    ]
      .filter(Boolean)
      .join('\n');

    // Build the response (what the companion did)
    const response = [
      `Action: ${action.description}`,
      `Result: ${outcome.description}`,
      outcome.success ? 'Outcome: SUCCESS' : 'Outcome: FAILURE',
      `Effect: ${outcome.numericResult > 0 ? '+' : ''}${outcome.numericResult}`,
    ].join('\n');

    // Quality score = safety × success_factor × confidence
    const successFactor = outcome.success ? 1.0 : 0.3;
    const qualityScore =
      outcome.safetyScore * successFactor * Math.max(action.confidence, 0.5);

    return {
      pairId: `sft_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      sourceRecordId: record.recordId,
      companionId: this._companionId,
      instruction,
      response,
      category: event.eventType,
      qualityScore: Math.min(1.0, qualityScore),
      timestamp: Date.now() / 1000,
    };
  }

  // -------------------------------------------------------------------------
  //  HuggingFace Push
  // -------------------------------------------------------------------------

  /**
   * Create a batch of unpushed SFT pairs for HuggingFace upload.
   * Returns null if no pairs are ready.
   */
  createBatch(): HFBatch | null {
    const unpushed = this._pairs.filter(
      (p) => !this._batches.some((b) => b.pairs.some((bp) => bp.pairId === p.pairId))
    );

    if (unpushed.length === 0) return null;

    const batch: HFBatch = {
      batchId: `batch_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      companionId: this._companionId,
      pairs: [...unpushed],
      datasetRepo: this._datasetRepo,
      pushedAt: null,
      status: 'pending',
    };

    this._batches.push(batch);
    return batch;
  }

  /**
   * Mark a batch as pushed (called after successful HF upload).
   */
  markBatchPushed(batchId: string): boolean {
    const batch = this._batches.find((b) => b.batchId === batchId);
    if (!batch || batch.status !== 'pending') return false;

    (batch as { status: string }).status = 'pushed';
    (batch as { pushedAt: number | null }).pushedAt = Date.now() / 1000;
    return true;
  }

  /**
   * Format batch as JSONL lines for HuggingFace upload.
   */
  batchToJSONL(batchId: string): string | null {
    const batch = this._batches.find((b) => b.batchId === batchId);
    if (!batch) return null;

    return batch.pairs
      .map((pair) =>
        JSON.stringify({
          id: pair.pairId,
          category: pair.category,
          instruction: pair.instruction,
          response: pair.response,
          metadata: {
            source: 'spiral_forge_gameplay',
            version: '1.0.0',
            companion_id: pair.companionId,
            quality_score: pair.qualityScore,
            timestamp: pair.timestamp,
          },
        })
      )
      .join('\n');
  }

  // -------------------------------------------------------------------------
  //  Fine-Tune Job Management
  // -------------------------------------------------------------------------

  /**
   * Check if there are enough approved pairs to trigger a fine-tune.
   */
  canTriggerFineTune(): boolean {
    const pushedPairs = this._batches
      .filter((b) => b.status === 'pushed')
      .reduce((sum, b) => sum + b.pairs.length, 0);
    return pushedPairs >= FINE_TUNE_THRESHOLD;
  }

  /**
   * Create a fine-tune job. Returns the job, or null if not enough data.
   */
  createFineTuneJob(): FineTuneJob | null {
    if (!this.canTriggerFineTune()) return null;

    const pushedBatches = this._batches.filter((b) => b.status === 'pushed');
    const totalPairs = pushedBatches.reduce((sum, b) => sum + b.pairs.length, 0);

    const job: FineTuneJob = {
      jobId: `ft_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      companionId: this._companionId,
      datasetRepo: this._datasetRepo,
      modelRepo: this._modelRepo,
      batchIds: pushedBatches.map((b) => b.batchId),
      totalPairs,
      startedAt: Date.now() / 1000,
      completedAt: null,
      status: 'queued',
      checkpointHash: null,
    };

    this._jobs.push(job);
    return job;
  }

  /**
   * Mark a fine-tune job as completed with a model checkpoint.
   */
  completeFineTuneJob(jobId: string, checkpointHash: string): boolean {
    const job = this._jobs.find((j) => j.jobId === jobId);
    if (!job || job.status === 'completed') return false;

    job.status = 'completed';
    job.completedAt = Date.now() / 1000;
    job.checkpointHash = checkpointHash;
    return true;
  }

  // -------------------------------------------------------------------------
  //  Queries
  // -------------------------------------------------------------------------

  /** Get all records in a specific tier */
  getRecordsByTier(tier: DatasetTier): readonly DatasetRecord[] {
    return this._records.filter((r) => r.tier === tier);
  }

  /** Get all SFT pairs */
  getPairs(): readonly SFTPair[] {
    return this._pairs;
  }

  /** Get all batches */
  getBatches(): readonly HFBatch[] {
    return this._batches;
  }

  /** Get all fine-tune jobs */
  getJobs(): readonly FineTuneJob[] {
    return this._jobs;
  }

  /** Get total record count */
  get totalRecords(): number {
    return this._records.length;
  }

  /** Get total pair count */
  get totalPairs(): number {
    return this._pairs.length;
  }

  /** Summary for UI display */
  summary(): {
    companionId: string;
    rawCount: number;
    quarantinedCount: number;
    approvedCount: number;
    sftPairCount: number;
    batchesPushed: number;
    batchesPending: number;
    fineTuneJobs: number;
    fineTuneCompleted: number;
    latestCheckpoint: string | null;
    datasetRepo: string;
    modelRepo: string;
  } {
    const latestCompletedJob = this._jobs
      .filter((j) => j.status === 'completed')
      .sort((a, b) => (b.completedAt ?? 0) - (a.completedAt ?? 0))[0];

    return {
      companionId: this._companionId,
      rawCount: this._records.filter((r) => r.tier === 'RAW').length,
      quarantinedCount: this._records.filter((r) => r.tier === 'QUARANTINED').length,
      approvedCount: this._records.filter((r) => r.tier === 'APPROVED').length,
      sftPairCount: this._pairs.length,
      batchesPushed: this._batches.filter((b) => b.status === 'pushed').length,
      batchesPending: this._batches.filter((b) => b.status === 'pending').length,
      fineTuneJobs: this._jobs.length,
      fineTuneCompleted: this._jobs.filter((j) => j.status === 'completed').length,
      latestCheckpoint: latestCompletedJob?.checkpointHash ?? null,
      datasetRepo: this._datasetRepo,
      modelRepo: this._modelRepo,
    };
  }
}

// ---------------------------------------------------------------------------
//  Adventure Session — Ties energy tokens + events + training together
// ---------------------------------------------------------------------------

/**
 * An adventure session links Energy Token consumption to training data generation.
 * When a player pays tokens for a dungeon run, this session captures all events,
 * pipes them through the training pipeline, and tracks the full audit trail.
 */
export interface AdventureSession {
  readonly sessionId: string;
  readonly playerId: string;
  readonly companionId: string;
  readonly activityType: string;

  /** Energy token consumption record (proof of payment) */
  readonly consumptionRecord: ConsumptionRecord;

  /** Events captured during this adventure */
  readonly events: GameEvent[];

  /** Training pipeline results */
  readonly trainingResult: {
    approved: number;
    quarantined: number;
    rejected: number;
    sftPairsGenerated: number;
  } | null;

  readonly startedAt: number;
  completedAt: number | null;
}

/**
 * Create a helper to build game events for testing / production.
 */
export function createGameEvent(
  sessionId: string,
  playerId: string,
  companionId: string,
  eventType: GameEventType,
  context: EventContext,
  action: EventAction,
  outcome: EventOutcome
): GameEvent {
  return {
    eventId: `evt_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    sessionId,
    playerId,
    companionId,
    eventType,
    timestamp: Date.now() / 1000,
    context,
    action,
    outcome,
  };
}
