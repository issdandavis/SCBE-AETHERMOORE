/**
 * AetherMore Roundabout City - governance-first routing hubs.
 *
 * This module models non-linear "roundabout" routing where every handoff
 * emits both a StateVector and DecisionRecord.
 *
 * @module agentic/roundabout-city
 */

export type GovernanceAction = 'ALLOW' | 'QUARANTINE' | 'DENY';

export type RoundaboutId = 'R0' | 'R1' | 'R2' | 'R3';

export type RoundaboutExit =
  | 'normalize_lane'
  | 'drop_lane'
  | 'quarantine_lane'
  | 'allow_lane'
  | 'shadow_lane'
  | 'human_review_lane'
  | 'execute_lane'
  | 'simulate_first_lane'
  | 'deny_noise_lane'
  | 'dataset_candidate_lane'
  | 'retrain_queue_lane'
  | 'discard_lane';

export interface StateVector {
  requestId: string;
  trustScore: number;
  riskScore: number;
  coherenceScore: number;
  timestamp: number;
  roundabout: RoundaboutId;
  selectedExit: RoundaboutExit;
  metadata?: Record<string, unknown>;
}

export interface DecisionRecord {
  requestId: string;
  action: GovernanceAction;
  reason: string;
  confidence: number;
  signature: string;
  timestamp: number;
  roundabout: RoundaboutId;
}

export interface GovernanceInput {
  requestId: string;
  trustScore: number; // [0,1]
  riskScore: number; // [0,1]
  coherenceScore: number; // [0,1]
  humanReviewRequired?: boolean;
  executionRequested?: boolean;
}

export interface RoundaboutDecision {
  stateVector: StateVector;
  decisionRecord: DecisionRecord;
  nextRoundabout?: RoundaboutId;
}

export interface RoundaboutThresholds {
  dropRisk: number;
  quarantineRisk: number;
  denyRisk: number;
  lowTrust: number;
  lowCoherence: number;
}

const DEFAULT_THRESHOLDS: RoundaboutThresholds = {
  dropRisk: 0.98,
  quarantineRisk: 0.75,
  denyRisk: 0.92,
  lowTrust: 0.35,
  lowCoherence: 0.45,
};

/**
 * Roundabout governance engine.
 *
 * It routes through four hubs:
 * - R0 Intake
 * - R1 Trust
 * - R2 Risk
 * - R3 Learning
 */
export class DecisionRoundabouts {
  private readonly thresholds: RoundaboutThresholds;

  constructor(thresholds: Partial<RoundaboutThresholds> = {}) {
    this.thresholds = { ...DEFAULT_THRESHOLDS, ...thresholds };
  }

  public route(input: GovernanceInput): RoundaboutDecision[] {
    const steps: RoundaboutDecision[] = [];

    const r0 = this.routeR0(input);
    steps.push(r0);
    if (r0.decisionRecord.action === 'DENY') return steps;

    const r1 = this.routeR1(input);
    steps.push(r1);
    if (r1.decisionRecord.action === 'DENY') return steps;

    const r2 = this.routeR2(input);
    steps.push(r2);

    if (r2.decisionRecord.action !== 'DENY') {
      steps.push(this.routeR3(input, r2.decisionRecord.action));
    }

    return steps;
  }

  public createExecutionTicket(input: GovernanceInput): {
    stateVector: StateVector;
    decisionRecord: DecisionRecord;
  } {
    const path = this.route(input);
    const r2 = path.find((p) => p.decisionRecord.roundabout === 'R2') || path[path.length - 1];
    return { stateVector: r2.stateVector, decisionRecord: r2.decisionRecord };
  }

  private routeR0(input: GovernanceInput): RoundaboutDecision {
    if (input.riskScore >= this.thresholds.dropRisk) {
      return this.makeDecision(
        input,
        'R0',
        'drop_lane',
        'DENY',
        'R0 drop lane: risk exceeds hard intake ceiling.',
        0.99
      );
    }

    if (input.riskScore >= this.thresholds.quarantineRisk) {
      return this.makeDecision(
        input,
        'R0',
        'quarantine_lane',
        'QUARANTINE',
        'R0 quarantine lane: elevated intake risk.',
        0.86
      );
    }

    return this.makeDecision(
      input,
      'R0',
      'normalize_lane',
      'ALLOW',
      'R0 normalize lane: intake accepted.',
      0.84
    );
  }

  private routeR1(input: GovernanceInput): RoundaboutDecision {
    if (input.humanReviewRequired) {
      return this.makeDecision(
        input,
        'R1',
        'human_review_lane',
        'QUARANTINE',
        'R1 human review lane: explicit HITL requirement.',
        0.9
      );
    }

    if (
      input.trustScore < this.thresholds.lowTrust ||
      input.coherenceScore < this.thresholds.lowCoherence
    ) {
      return this.makeDecision(
        input,
        'R1',
        'shadow_lane',
        'QUARANTINE',
        'R1 shadow lane: trust/coherence below threshold.',
        0.88
      );
    }

    return this.makeDecision(
      input,
      'R1',
      'allow_lane',
      'ALLOW',
      'R1 allow lane: trust and coherence accepted.',
      0.83
    );
  }

  private routeR2(input: GovernanceInput): RoundaboutDecision {
    if (input.riskScore >= this.thresholds.denyRisk) {
      return this.makeDecision(
        input,
        'R2',
        'deny_noise_lane',
        'DENY',
        'R2 deny+noise lane: harmonic wall exceeded.',
        0.97
      );
    }

    if (input.executionRequested && input.riskScore < this.thresholds.quarantineRisk) {
      return this.makeDecision(
        input,
        'R2',
        'execute_lane',
        'ALLOW',
        'R2 execute lane: governed execution approved.',
        0.89
      );
    }

    return this.makeDecision(
      input,
      'R2',
      'simulate_first_lane',
      'QUARANTINE',
      'R2 simulate-first lane: execution deferred to safe simulation.',
      0.85
    );
  }

  private routeR3(input: GovernanceInput, priorAction: GovernanceAction): RoundaboutDecision {
    if (priorAction === 'DENY') {
      return this.makeDecision(
        input,
        'R3',
        'discard_lane',
        'DENY',
        'R3 discard lane: denied path is not eligible for learning.',
        0.95
      );
    }

    if (priorAction === 'QUARANTINE') {
      return this.makeDecision(
        input,
        'R3',
        'retrain_queue_lane',
        'QUARANTINE',
        'R3 retrain queue lane: quarantined path sent for model hardening.',
        0.87
      );
    }

    return this.makeDecision(
      input,
      'R3',
      'dataset_candidate_lane',
      'ALLOW',
      'R3 dataset candidate lane: approved for curated learning.',
      0.82
    );
  }

  private makeDecision(
    input: GovernanceInput,
    roundabout: RoundaboutId,
    exit: RoundaboutExit,
    action: GovernanceAction,
    reason: string,
    confidence: number
  ): RoundaboutDecision {
    const now = Date.now();
    const stateVector: StateVector = {
      requestId: input.requestId,
      trustScore: input.trustScore,
      riskScore: input.riskScore,
      coherenceScore: input.coherenceScore,
      timestamp: now,
      roundabout,
      selectedExit: exit,
      metadata: {
        humanReviewRequired: !!input.humanReviewRequired,
        executionRequested: !!input.executionRequested,
      },
    };

    const decisionRecord: DecisionRecord = {
      requestId: input.requestId,
      action,
      reason,
      confidence,
      signature: `scbe-roundabout-${roundabout}`,
      timestamp: now,
      roundabout,
    };

    return { stateVector, decisionRecord };
  }
}
