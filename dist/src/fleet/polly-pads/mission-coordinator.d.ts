/**
 * @file mission-coordinator.ts
 * @module fleet/polly-pads/mission-coordinator
 *
 * Dual-surface coordinator module:
 * 1) Legacy coordinator for ModePad + Core Squad integration (`setPhase`, `handleCrisis`).
 * 2) Compatibility coordinator + BFT squad API used by v2 Polly Pad tests.
 */
import { Squad as CoreSquad } from './squad';
import { CrisisType, ModeAssignment, SpecialistMode } from './modes/types';
import { Squad } from './squad';
export type MissionPhase = 'transit' | 'science_ops' | 'maintenance' | 'crisis' | 'earth_sync' | 'standby';
export interface CrisisAssessment {
    type: CrisisType;
    severity: number;
    assignments: ModeAssignment[];
    requiresEarthContact: boolean;
    estimatedResolutionMinutes: number;
    assessedAt: number;
}
interface PhaseConfig {
    defaultModes: SpecialistMode[];
    description: string;
}
export declare const BFT: {
    readonly QUORUM: {
        readonly routine: 3;
        readonly critical: 4;
        readonly destructive: 5;
    };
};
export type VoteDecision = 'APPROVE' | 'REJECT' | 'DEFER';
export interface Vote {
    padId: string;
    decision: VoteDecision;
    confidence: number;
    timestamp: number;
}
export interface VotingSession {
    id: string;
    proposal: string;
    proposerId: string;
    severity: keyof typeof BFT.QUORUM;
    status: 'open' | 'approved' | 'rejected';
    votes: Vote[];
    createdAt: number;
}
export interface SquadMember {
    padId: string;
    healthy: boolean;
    lastHeartbeat: number;
}
export interface ConsensusResult {
    approved: boolean;
    approveCount: number;
    rejectCount: number;
    deferCount: number;
    quorumRequired: number;
}
export declare class Squad {
    readonly id: string;
    private readonly maxMembers;
    private members;
    private assignments;
    private sessions;
    constructor(id: string);
    addMember(padId: string): void;
    getMembers(): SquadMember[];
    get healthyCount(): number;
    get hasBftQuorum(): boolean;
    assignMode(padId: string, mode: SpecialistMode): void;
    getAssignedMode(padId: string): SpecialistMode | null;
    createVotingSession(proposal: string, proposerId: string, severity: keyof typeof BFT.QUORUM): VotingSession;
    castVote(sessionId: string, vote: Vote): void;
    checkConsensus(sessionId: string): ConsensusResult;
    getSession(sessionId: string): VotingSession | null;
    checkHealth(staleThresholdMs: number): string[];
}
export declare class MissionCoordinator {
    private legacySquad;
    private squads;
    private _currentPhase;
    private _activeCrisis;
    private phaseHistory;
    private crisisHistory;
    constructor(squad?: CoreSquad);
    get currentPhase(): MissionPhase;
    get activeCrisis(): CrisisAssessment | null;
    setPhase(phase: MissionPhase): ModeAssignment[];
    handleCrisis(crisisType: CrisisType, severity?: number): CrisisAssessment;
    resolveCrisis(returnPhase?: MissionPhase): ModeAssignment[];
    assessCrisis(crisisType: CrisisType, severity?: number): CrisisAssessment;
    getPhaseConfig(phase: MissionPhase): PhaseConfig;
    getCrisisHistory(): CrisisAssessment[];
    getPhaseHistory(): Array<{
        phase: MissionPhase;
        timestamp: number;
    }>;
    registerSquad(squad: Squad): void;
    assignDefaultModes(squadId: string, mode: SpecialistMode): void;
    getRecommendedAssignment(squadId: string, crisisType: CrisisType | 'power_emergency'): Map<string, SpecialistMode>;
    executeCrisisReassignment(squadId: string, crisisType: CrisisType | 'power_emergency', immediate: boolean): {
        assignment: Map<string, SpecialistMode>;
        session?: VotingSession;
    };
    applyAssignment(squadId: string, assignment: Map<string, SpecialistMode>): void;
}
export {};
//# sourceMappingURL=mission-coordinator.d.ts.map