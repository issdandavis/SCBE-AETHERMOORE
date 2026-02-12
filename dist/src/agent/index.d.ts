/**
 * Agent Module Exports
 *
 * Provides agent lifecycle management, swarm coordination,
 * and Kafka event publishing for SCBE-AETHERMOORE.
 *
 * @module agent
 */
export { type IPTier, type AgentStatus, type AgentEventType, type PoincarePosition, type AgentKeys, type AgentConfig, type Agent, type AgentHeartbeat, type AgentEvent, type BFTConfig, type BFTVote, type BFTConsensusResult, type SwarmState, type FormationTarget, type AgentHealth, type RogueDetectionResult, GOLDEN_RATIO, TONGUE_PHASES, TONGUE_INDICES, TONGUE_IP_TIERS, HEARTBEAT_INTERVAL_MS, AGENT_TIMEOUT_MS, COHERENCE_DECAY_RATE, calculateTongueWeight, phaseToRadians, poincareNorm, isValidPoincarePosition, hyperbolicDistance, harmonicWallCost, generateInitialPosition, calculateBFTQuorum, } from './types.js';
export { type LifecycleHandlers, type AgentManagerConfig, AgentManager, AgentMonitor, isAgentDead, createAgentManager, createAgentConfig, } from './lifecycle.js';
export { MIN_COHERENCE_THRESHOLD, MAX_HYPERBOLIC_DISTANCE, ROGUE_QUARANTINE_THRESHOLD, mobiusAdd, mobiusScale, hyperbolicCentroid, generateRingFormation, generateDispersedFormation, generateConvergentFormation, createFormationTarget, SwarmCoordinator, collectVotes, weightedVoteCount, runWeightedConsensus, detectRogueAgent, quarantineAgent, } from './swarm.js';
export { type KafkaMessage, type KafkaProducer, type KafkaConsumer, type KafkaConfig, type AgentEventHandler, getTopicName, getTierTopicPattern, getAgentTopics, parseTopicName, MockKafkaClient, AgentEventPublisher, AgentEventSubscriber, createKafkaClient, createEventPublisher, createEventSubscriber, } from './kafka.js';
//# sourceMappingURL=index.d.ts.map