/**
 * Agent Module Exports
 *
 * Provides agent lifecycle management, swarm coordination,
 * and Kafka event publishing for SCBE-AETHERMOORE.
 *
 * @module agent
 */

// Types
export {
  // Core types
  type IPTier,
  type AgentStatus,
  type AgentEventType,
  type PoincarePosition,
  type AgentKeys,
  type AgentConfig,
  type Agent,
  type AgentHeartbeat,
  type AgentEvent,

  // BFT types
  type BFTConfig,
  type BFTVote,
  type BFTConsensusResult,

  // Swarm types
  type SwarmState,
  type FormationTarget,

  // Health types
  type AgentHealth,
  type RogueDetectionResult,

  // Constants
  GOLDEN_RATIO,
  TONGUE_PHASES,
  TONGUE_INDICES,
  TONGUE_IP_TIERS,
  HEARTBEAT_INTERVAL_MS,
  AGENT_TIMEOUT_MS,
  COHERENCE_DECAY_RATE,

  // Utility functions
  calculateTongueWeight,
  phaseToRadians,
  poincareNorm,
  isValidPoincarePosition,
  hyperbolicDistance,
  harmonicWallCost,
  generateInitialPosition,
  calculateBFTQuorum,
} from './types.js';

// Lifecycle
export {
  type LifecycleHandlers,
  type AgentManagerConfig,
  AgentManager,
  AgentMonitor,
  isAgentDead,
  createAgentManager,
  createAgentConfig,
} from './lifecycle.js';

// Swarm
export {
  // Constants
  MIN_COHERENCE_THRESHOLD,
  MAX_HYPERBOLIC_DISTANCE,
  ROGUE_QUARANTINE_THRESHOLD,

  // Hyperbolic operations
  mobiusAdd,
  mobiusScale,
  hyperbolicCentroid,

  // Formation
  generateRingFormation,
  generateDispersedFormation,
  generateConvergentFormation,
  createFormationTarget,

  // Swarm coordinator
  SwarmCoordinator,

  // BFT consensus
  collectVotes,
  weightedVoteCount,
  runWeightedConsensus,

  // Rogue detection
  detectRogueAgent,
  quarantineAgent,
} from './swarm.js';

// Kafka
export {
  type KafkaMessage,
  type KafkaProducer,
  type KafkaConsumer,
  type KafkaConfig,
  type AgentEventHandler,

  // Topic naming
  getTopicName,
  getTierTopicPattern,
  getAgentTopics,
  parseTopicName,

  // Mock client (for testing)
  MockKafkaClient,

  // Event publishing
  AgentEventPublisher,
  AgentEventSubscriber,

  // Factory functions
  createKafkaClient,
  createEventPublisher,
  createEventSubscriber,
} from './kafka.js';
