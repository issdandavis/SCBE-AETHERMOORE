/**
 * @file index.ts
 * @module conference/shared/types
 *
 * Core type definitions for the Vibe Coder Conference App.
 *
 * Three roles: Vibe Coders (creators), Investors (funders), Curators (protocol).
 * Every project flows through: Intake → SCBE/HYDRA Governance → Conference & Funding.
 */

// ═══════════════════════════════════════════════════════════════
// Identity & Auth
// ═══════════════════════════════════════════════════════════════

export type UserRole = 'coder' | 'investor' | 'curator';

export interface User {
  id: string;
  email: string;
  displayName: string;
  role: UserRole;
  avatarUrl?: string;
  createdAt: string;
  /** For investors: KYC verification status */
  kycStatus?: 'pending' | 'verified' | 'rejected';
  /** For investors: wallet address for on-chain binding (optional) */
  walletAddress?: string;
}

// ═══════════════════════════════════════════════════════════════
// Project Capsule (Intake)
// ═══════════════════════════════════════════════════════════════

export type ProjectStatus =
  | 'draft'
  | 'submitted'
  | 'scoring'
  | 'allowed'
  | 'quarantined'
  | 'denied'
  | 'scheduled'
  | 'presented'
  | 'funded';

export interface ProjectCapsule {
  id: string;
  /** Immutable SCBE identity across all layers and events */
  scbeId: string;
  creatorId: string;
  title: string;
  tagline: string;
  description: string;
  techStack: string[];
  repoUrl?: string;
  demoUrl?: string;
  videoUrl?: string;
  pitchDeckUrl?: string;
  fundingAsk: FundingAsk;
  status: ProjectStatus;
  /** SCBE governance scores — populated after pipeline run */
  governance?: GovernanceResult;
  /** HYDRA swarm browser audit — populated after crawl */
  hydraAudit?: HydraAuditResult;
  submittedAt?: string;
  createdAt: string;
  updatedAt: string;
}

export interface FundingAsk {
  /** Amount in USD */
  amount: number;
  /** What the money is for */
  useOfFunds: string;
  /** Current stage */
  stage: 'pre-seed' | 'seed' | 'series-a' | 'grant' | 'other';
}

// ═══════════════════════════════════════════════════════════════
// SCBE Governance (L1-L14 Pipeline Results)
// ═══════════════════════════════════════════════════════════════

/** SCBE 14-layer pipeline decision */
export type GovernanceDecision = 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY';

export interface GovernanceResult {
  /** Final decision from L13 */
  decision: GovernanceDecision;
  /** Coherence score from L9-L10 [0, 1] */
  coherence: number;
  /** Hyperbolic distance from safe center (L5) */
  hyperbolicDistance: number;
  /** Harmonic scaling score from L12 [0, 1] */
  harmonicScore: number;
  /** Novelty score (higher = more novel/unusual) */
  noveltyScore: number;
  /** Risk posture label for display */
  riskLabel: 'low' | 'medium' | 'high' | 'critical';
  /** Layer-by-layer summary for audit */
  layerSummary: LayerScore[];
  /** Timestamp of scoring run */
  scoredAt: string;
}

export interface LayerScore {
  layer: number;
  name: string;
  score: number;
  passed: boolean;
  note?: string;
}

// ═══════════════════════════════════════════════════════════════
// HYDRA Swarm Audit
// ═══════════════════════════════════════════════════════════════

export interface HydraAuditResult {
  /** Which tongue agents participated */
  agents: HydraAgentReport[];
  /** Overall quality heuristic [0, 1] */
  qualityScore: number;
  /** Security flags from browser crawl */
  securityFlags: string[];
  /** Provenance checks (license, attribution) */
  provenanceFlags: string[];
  /** Quorum: did enough agents agree on the assessment? */
  quorumMet: boolean;
  /** Phase-lock score between agents during assessment */
  phaseLockScore: number;
  auditedAt: string;
}

export interface HydraAgentReport {
  tongue: 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';
  role: string;
  findings: string[];
  score: number;
}

// ═══════════════════════════════════════════════════════════════
// NDA & Access Control
// ═══════════════════════════════════════════════════════════════

export type NDAStatus = 'pending' | 'sent' | 'signed' | 'expired' | 'revoked';

export interface NDARecord {
  id: string;
  investorId: string;
  /** null = platform-wide NDA; string = project-specific */
  projectId: string | null;
  templateId: string;
  status: NDAStatus;
  /** External e-signature envelope ID (DocuSign / similar) */
  envelopeId?: string;
  signedAt?: string;
  expiresAt?: string;
  createdAt: string;
}

/** What the investor can see based on NDA status */
export interface AccessLevel {
  canViewPublicProfile: boolean;
  canViewFullDeck: boolean;
  canAccessDataRoom: boolean;
  canJoinLiveQA: boolean;
  canSoftCommit: boolean;
  ndaRequired: boolean;
  ndaSigned: boolean;
}

// ═══════════════════════════════════════════════════════════════
// Conference / Demo Day
// ═══════════════════════════════════════════════════════════════

export type ConferenceStatus = 'draft' | 'scheduled' | 'live' | 'ended' | 'archived';

export interface Conference {
  id: string;
  title: string;
  theme: string;
  description: string;
  status: ConferenceStatus;
  scheduledAt: string;
  /** Duration in minutes */
  duration: number;
  /** Ordered list of project slots */
  slots: ConferenceSlot[];
  /** Stream URL (populated when live) */
  streamUrl?: string;
  createdAt: string;
}

export interface ConferenceSlot {
  id: string;
  projectId: string;
  /** Order in the lineup */
  order: number;
  /** Slot duration in minutes */
  durationMinutes: number;
  /** Pitch + Q&A breakdown */
  pitchMinutes: number;
  qaMinutes: number;
  status: 'upcoming' | 'live' | 'completed';
}

// ═══════════════════════════════════════════════════════════════
// Funding / Soft Commits
// ═══════════════════════════════════════════════════════════════

export interface SoftCommit {
  id: string;
  investorId: string;
  projectId: string;
  conferenceId: string;
  /** Amount in USD (non-binding) */
  amount: number;
  /** Preset tier used */
  tier: '10k' | '25k' | '50k' | '100k' | 'custom';
  /** Interest level */
  interestLevel: 'interested' | 'strong' | 'lead';
  /** Optional note to creator */
  note?: string;
  createdAt: string;
}

export interface DealRoom {
  id: string;
  projectId: string;
  /** Only NDA-cleared investors can access */
  investorIds: string[];
  /** Cap table, roadmap, SCBE audit summary */
  documents: DealDocument[];
  status: 'open' | 'closed' | 'funded';
  totalSoftCommits: number;
  createdAt: string;
}

export interface DealDocument {
  id: string;
  name: string;
  type: 'cap_table' | 'roadmap' | 'scbe_audit' | 'financials' | 'legal' | 'other';
  url: string;
  uploadedAt: string;
}

// ═══════════════════════════════════════════════════════════════
// Live Conference Events (WebSocket)
// ═══════════════════════════════════════════════════════════════

export type LiveEventType =
  | 'slot:start'
  | 'slot:end'
  | 'commit:new'
  | 'commit:ticker'
  | 'reaction'
  | 'chat:message'
  | 'governance:alert'
  | 'phase:update';

export interface LiveEvent {
  type: LiveEventType;
  conferenceId: string;
  timestamp: string;
  payload: Record<string, unknown>;
}

// ═══════════════════════════════════════════════════════════════
// API Response Wrappers
// ═══════════════════════════════════════════════════════════════

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  meta?: {
    total?: number;
    page?: number;
    limit?: number;
  };
}
