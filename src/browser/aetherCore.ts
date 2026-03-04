/**
 * @file aetherCore.ts
 * @module browser/aetherCore
 * @layer Layer 1-14 (Unified)
 * @component AetherCore — Unified AI Browser Controller
 * @version 1.0.0
 * @since 2026-03-04
 *
 * AetherCore inverts the typical AI-browser relationship:
 *
 *   Edge model:    Browser → AI sidebar  (AI can see some things, sometimes)
 *   Aether model:  AI Core → Browser as sensory organ  (AI sees EVERYTHING)
 *
 * The browser is a peripheral of the AI, not the other way around.
 * Vision is native. Every page state is continuously embedded into
 * the Poincaré ball. The governance gauge field (BitSpin + Chirality
 * + Phase Locking) runs continuously alongside browser operations.
 *
 * Architecture:
 * ┌─────────────────────────────────────────────────────────────┐
 * │                      AETHER CORE                            │
 * │  ┌──────────┐ ┌──────────┐ ┌──────────────────────────┐    │
 * │  │ Browser  │ │ Gauge    │ │ Intent-to-Action         │    │
 * │  │ Agent    │ │ Field    │ │ Pipeline                 │    │
 * │  │ (SCBE    │ │ (Spin +  │ │ (user intent → embed →   │    │
 * │  │  14-layer│ │ Chirality│ │  govern → action seq)    │    │
 * │  │  pipeline│ │ + Phase) │ │                          │    │
 * │  └────┬─────┘ └────┬─────┘ └────────────┬─────────────┘    │
 * │       │             │                    │                  │
 * │       └─────────────┴────────────────────┘                  │
 * │                     │                                       │
 * │              ┌──────┴──────┐                                │
 * │              │ Perception  │  ← continuous page awareness   │
 * │              │ Loop        │                                │
 * │              └──────┬──────┘                                │
 * │                     │                                       │
 * │              ┌──────┴──────┐                                │
 * │              │ Browser     │  ← CDP / Playwright / etc.     │
 * │              │ Backend     │                                │
 * │              └─────────────┘                                │
 * └─────────────────────────────────────────────────────────────┘
 *
 * @axiom A4: Symmetry — gauge invariance under tongue permutations
 * @axiom A2: Unitarity — charge conservation across governance blocks
 * @axiom A3: Causality — action ordering preserved in governance chain
 */

import { randomUUID } from 'crypto';
import { GovernanceGaugeField } from '../harmonic/governanceGaugeField.js';
import type { GovernanceBlock } from '../harmonic/governanceGaugeField.js';
import { BrowserAgent, MockBrowserBackend } from './agent.js';
import type { BrowserBackend, BrowserAgentConfig } from './agent.js';
import type { BrowserAction, ActionResult, PageObservation } from './types.js';
import { TongueCode } from '../tokenizer/ss1.js';

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

/**
 * AetherCore configuration.
 */
export interface AetherCoreConfig {
  /** Agent identifier */
  agentId?: string;
  /** Sacred Tongue assignment */
  tongue?: TongueCode;
  /** Browser backend instance */
  backend?: BrowserBackend;
  /** Number of governance arrays (more = stronger consensus) */
  governanceArrayCount?: number;
  /** Gauge field coupling constant */
  couplingConstant?: number;
  /** Ticks per governance evaluation */
  gaugeTicksPerAction?: number;
  /** Lagrangian thresholds for risk decisions */
  lagrangianThresholds?: {
    allow: number;
    quarantine: number;
    escalate: number;
  };
  /** Auto-screenshot on every action */
  autoScreenshot?: boolean;
  /** Max actions per session */
  maxActions?: number;
}

/**
 * Result of intent processing through the full pipeline.
 */
export interface IntentResult {
  /** Original intent description */
  intent: string;
  /** Actions derived from intent */
  actions: BrowserAction[];
  /** Results of executing each action */
  results: ActionResult[];
  /** Governance block forged after evaluation */
  governanceBlock: GovernanceBlock;
  /** Overall success */
  success: boolean;
  /** Field Lagrangian at decision time */
  lagrangian: number;
  /** Consensus strength across governance arrays */
  consensus: number;
  /** Total duration (ms) */
  duration: number;
}

/**
 * Perception snapshot — what the AI "sees" right now.
 */
export interface PerceptionSnapshot {
  /** Current page observation */
  page: PageObservation | null;
  /** Current governance gauge field state */
  gaugeState: {
    lagrangian: number;
    consensus: number;
    tick: number;
    latestBlock: GovernanceBlock | null;
  };
  /** Timestamp */
  timestamp: number;
}

/**
 * AetherCore lifecycle state.
 */
export type AetherCoreState = 'idle' | 'active' | 'perceiving' | 'governing' | 'executing';

// ═══════════════════════════════════════════════════════════════
// AetherCore
// ═══════════════════════════════════════════════════════════════

/**
 * AetherCore — the unified AI browser controller.
 *
 * Owns the browser as a sensory organ. The AI perceives through
 * the browser, governs through the gauge field, and executes
 * through the backend. All three layers are always-on.
 *
 * Key differentiator from Edge/Arc/etc:
 * - Vision is native (every page state → Poincaré embedding)
 * - Governance is geometric (adversarial actions cost exponentially more)
 * - Multi-array consensus via phase-locked breathing transforms
 * - Spin + chirality fields detect anomalous browser behavior
 * - Governance blocks are "chained" through harmonic phase continuity
 */
export class AetherCore {
  readonly id: string;
  private state: AetherCoreState = 'idle';

  /** The browser agent (SCBE 14-layer governed) */
  private agent: BrowserAgent;

  /** The governance gauge field (spin + chirality + phase locking) */
  private gaugeField: GovernanceGaugeField;

  /** Configuration */
  private config: Required<AetherCoreConfig>;

  /** Last perception snapshot */
  private lastPerception: PerceptionSnapshot | null = null;

  /** Action counter */
  private actionCounter = 0;

  constructor(config: AetherCoreConfig = {}) {
    this.id = config.agentId ?? `aether-${randomUUID().slice(0, 8)}`;

    this.config = {
      agentId: this.id,
      tongue: config.tongue ?? ('KO' as TongueCode),
      backend: config.backend ?? new MockBrowserBackend(),
      governanceArrayCount: config.governanceArrayCount ?? 2,
      couplingConstant: config.couplingConstant ?? 1.0,
      gaugeTicksPerAction: config.gaugeTicksPerAction ?? 5,
      lagrangianThresholds: config.lagrangianThresholds ?? {
        allow: 5.0,
        quarantine: 15.0,
        escalate: 30.0,
      },
      autoScreenshot: config.autoScreenshot ?? false,
      maxActions: config.maxActions ?? 500,
    };

    // Create the browser agent
    const agentConfig: BrowserAgentConfig = {
      agentId: this.id,
      tongue: this.config.tongue,
      backend: this.config.backend,
      autoScreenshot: this.config.autoScreenshot,
      maxActions: this.config.maxActions,
    };
    this.agent = new BrowserAgent(agentConfig);

    // Create the governance gauge field
    this.gaugeField = new GovernanceGaugeField({
      samplesPerTick: 3,
      breathAmplitude: 0.05,
      phaseLockThreshold: 0.7,
      lagrangianThresholds: this.config.lagrangianThresholds,
      couplingConstant: this.config.couplingConstant,
    });

    // Initialize governance arrays
    for (let i = 0; i < this.config.governanceArrayCount; i++) {
      this.gaugeField.createArray(`array-${i}`, i);
    }
  }

  // ═══════════════════════════════════════════════════════════════
  // Lifecycle
  // ═══════════════════════════════════════════════════════════════

  /**
   * Start the AetherCore — initializes browser and begins perception.
   */
  async start(url?: string): Promise<void> {
    this.state = 'active';
    await this.agent.startSession(url);

    // Prime the gauge field with initial ticks
    for (let i = 0; i < this.config.gaugeTicksPerAction; i++) {
      this.gaugeField.tick();
    }

    // Forge initial governance block
    this.gaugeField.forgeBlock();
  }

  /**
   * Stop the AetherCore — closes browser and finalizes governance chain.
   */
  async stop(): Promise<{ governanceChain: readonly GovernanceBlock[] }> {
    // Forge final block
    this.gaugeField.forgeBlock();

    const summary = await this.agent.endSession();
    this.state = 'idle';

    return {
      governanceChain: this.gaugeField.getChain(),
    };
  }

  // ═══════════════════════════════════════════════════════════════
  // Perception — "what does the AI see right now?"
  // ═══════════════════════════════════════════════════════════════

  /**
   * Get current perception — page state + governance field state.
   *
   * This is the AI's "eyes". Every call gives a complete picture
   * of what's happening in the browser AND the governance field.
   */
  async perceive(): Promise<PerceptionSnapshot> {
    this.state = 'perceiving';

    let page: PageObservation | null = null;
    try {
      const obs = await this.agent.getObservation();
      page = obs.page;
    } catch {
      // Browser may not be connected yet
    }

    const chain = this.gaugeField.getChain();
    const latestBlock = chain.length > 0 ? chain[chain.length - 1] : null;

    const snapshot: PerceptionSnapshot = {
      page,
      gaugeState: {
        lagrangian: this.gaugeField.computeLagrangian(),
        consensus: this.gaugeField.consensusStrength(),
        tick: this.gaugeField.getTick(),
        latestBlock,
      },
      timestamp: Date.now(),
    };

    this.lastPerception = snapshot;
    this.state = 'active';
    return snapshot;
  }

  // ═══════════════════════════════════════════════════════════════
  // Action — execute governed browser actions
  // ═══════════════════════════════════════════════════════════════

  /**
   * Execute a single browser action with full governance.
   *
   * Flow:
   * 1. Tick gauge field (spin sampling + chirality propagation)
   * 2. Forge governance block (Lagrangian → risk decision)
   * 3. If block decision allows, execute via BrowserAgent
   * 4. Return combined result
   */
  async act(action: BrowserAction): Promise<ActionResult & { governanceBlock: GovernanceBlock }> {
    this.state = 'governing';
    const startTime = Date.now();

    // Evolve gauge field
    for (let i = 0; i < this.config.gaugeTicksPerAction; i++) {
      this.gaugeField.tick();
    }

    // Forge governance block
    const block = this.gaugeField.forgeBlock();

    // Check gauge field decision
    if (block.decision === 'DENY') {
      this.state = 'active';
      return {
        success: false,
        error: `Gauge field DENY: Lagrangian ${block.lagrangian.toFixed(3)} exceeds threshold`,
        duration: Date.now() - startTime,
        governanceBlock: block,
      };
    }

    // Execute through the browser agent's SCBE pipeline
    this.state = 'executing';
    const result = await this.agent.execute(action);
    this.actionCounter++;

    this.state = 'active';
    return {
      ...result,
      governanceBlock: block,
    };
  }

  /**
   * Navigate to URL.
   */
  async navigate(url: string): Promise<ActionResult & { governanceBlock: GovernanceBlock }> {
    return this.act({ type: 'navigate', url });
  }

  /**
   * Click element.
   */
  async click(selector: string): Promise<ActionResult & { governanceBlock: GovernanceBlock }> {
    return this.act({ type: 'click', selector });
  }

  /**
   * Type text.
   */
  async type(
    selector: string,
    text: string,
    options?: { clear?: boolean; sensitive?: boolean }
  ): Promise<ActionResult & { governanceBlock: GovernanceBlock }> {
    return this.act({
      type: 'type',
      selector,
      text,
      clear: options?.clear,
      sensitive: options?.sensitive,
    });
  }

  /**
   * Take screenshot (read-only, no governance gate).
   */
  async screenshot(): Promise<ActionResult & { governanceBlock: GovernanceBlock }> {
    return this.act({ type: 'screenshot' });
  }

  // ═══════════════════════════════════════════════════════════════
  // Intent Pipeline — "user says X, AI does Y"
  // ═══════════════════════════════════════════════════════════════

  /**
   * Process a user intent through the full pipeline.
   *
   * This is the high-level "do what I mean" interface.
   * The intent is decomposed into browser actions, each governed
   * independently through the gauge field.
   *
   * @param intent - Natural language description of what to do
   * @param actions - Pre-decomposed action sequence (skip NLU)
   * @returns Combined result with governance chain
   */
  async processIntent(
    intent: string,
    actions: BrowserAction[]
  ): Promise<IntentResult> {
    const startTime = Date.now();
    const results: ActionResult[] = [];
    let overallSuccess = true;

    for (const action of actions) {
      const result = await this.act(action);
      results.push(result);

      if (!result.success) {
        overallSuccess = false;
        // Stop on DENY, continue on other failures
        if (result.error?.includes('DENY')) break;
      }
    }

    // Forge a summary block
    const summaryBlock = this.gaugeField.forgeBlock();

    return {
      intent,
      actions,
      results,
      governanceBlock: summaryBlock,
      success: overallSuccess,
      lagrangian: this.gaugeField.computeLagrangian(),
      consensus: this.gaugeField.consensusStrength(),
      duration: Date.now() - startTime,
    };
  }

  // ═══════════════════════════════════════════════════════════════
  // Accessors
  // ═══════════════════════════════════════════════════════════════

  /** Get current state */
  getState(): AetherCoreState {
    return this.state;
  }

  /** Get the governance chain (all forged blocks) */
  getGovernanceChain(): readonly GovernanceBlock[] {
    return this.gaugeField.getChain();
  }

  /** Get the last perception snapshot */
  getLastPerception(): PerceptionSnapshot | null {
    return this.lastPerception;
  }

  /** Get action count */
  getActionCount(): number {
    return this.actionCounter;
  }

  /** Get the underlying browser agent (for advanced use) */
  getBrowserAgent(): BrowserAgent {
    return this.agent;
  }

  /** Get the underlying gauge field (for advanced use) */
  getGaugeField(): GovernanceGaugeField {
    return this.gaugeField;
  }
}

// ═══════════════════════════════════════════════════════════════
// Factory
// ═══════════════════════════════════════════════════════════════

/**
 * Create an AetherCore instance.
 *
 * @param config - Configuration options
 * @returns Configured AetherCore
 */
export function createAetherCore(config: AetherCoreConfig = {}): AetherCore {
  return new AetherCore(config);
}
