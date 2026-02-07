"use strict";
/**
 * Agent Module Exports
 *
 * Provides agent lifecycle management, swarm coordination,
 * and Kafka event publishing for SCBE-AETHERMOORE.
 *
 * @module agent
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.createEventSubscriber = exports.createEventPublisher = exports.createKafkaClient = exports.AgentEventSubscriber = exports.AgentEventPublisher = exports.MockKafkaClient = exports.parseTopicName = exports.getAgentTopics = exports.getTierTopicPattern = exports.getTopicName = exports.quarantineAgent = exports.detectRogueAgent = exports.runWeightedConsensus = exports.weightedVoteCount = exports.collectVotes = exports.SwarmCoordinator = exports.createFormationTarget = exports.generateConvergentFormation = exports.generateDispersedFormation = exports.generateRingFormation = exports.hyperbolicCentroid = exports.mobiusScale = exports.mobiusAdd = exports.ROGUE_QUARANTINE_THRESHOLD = exports.MAX_HYPERBOLIC_DISTANCE = exports.MIN_COHERENCE_THRESHOLD = exports.createAgentConfig = exports.createAgentManager = exports.isAgentDead = exports.AgentMonitor = exports.AgentManager = exports.calculateBFTQuorum = exports.generateInitialPosition = exports.harmonicWallCost = exports.hyperbolicDistance = exports.isValidPoincarePosition = exports.poincareNorm = exports.phaseToRadians = exports.calculateTongueWeight = exports.COHERENCE_DECAY_RATE = exports.AGENT_TIMEOUT_MS = exports.HEARTBEAT_INTERVAL_MS = exports.TONGUE_IP_TIERS = exports.TONGUE_INDICES = exports.TONGUE_PHASES = exports.GOLDEN_RATIO = void 0;
// Types
var types_js_1 = require("./types.js");
// Constants
Object.defineProperty(exports, "GOLDEN_RATIO", { enumerable: true, get: function () { return types_js_1.GOLDEN_RATIO; } });
Object.defineProperty(exports, "TONGUE_PHASES", { enumerable: true, get: function () { return types_js_1.TONGUE_PHASES; } });
Object.defineProperty(exports, "TONGUE_INDICES", { enumerable: true, get: function () { return types_js_1.TONGUE_INDICES; } });
Object.defineProperty(exports, "TONGUE_IP_TIERS", { enumerable: true, get: function () { return types_js_1.TONGUE_IP_TIERS; } });
Object.defineProperty(exports, "HEARTBEAT_INTERVAL_MS", { enumerable: true, get: function () { return types_js_1.HEARTBEAT_INTERVAL_MS; } });
Object.defineProperty(exports, "AGENT_TIMEOUT_MS", { enumerable: true, get: function () { return types_js_1.AGENT_TIMEOUT_MS; } });
Object.defineProperty(exports, "COHERENCE_DECAY_RATE", { enumerable: true, get: function () { return types_js_1.COHERENCE_DECAY_RATE; } });
// Utility functions
Object.defineProperty(exports, "calculateTongueWeight", { enumerable: true, get: function () { return types_js_1.calculateTongueWeight; } });
Object.defineProperty(exports, "phaseToRadians", { enumerable: true, get: function () { return types_js_1.phaseToRadians; } });
Object.defineProperty(exports, "poincareNorm", { enumerable: true, get: function () { return types_js_1.poincareNorm; } });
Object.defineProperty(exports, "isValidPoincarePosition", { enumerable: true, get: function () { return types_js_1.isValidPoincarePosition; } });
Object.defineProperty(exports, "hyperbolicDistance", { enumerable: true, get: function () { return types_js_1.hyperbolicDistance; } });
Object.defineProperty(exports, "harmonicWallCost", { enumerable: true, get: function () { return types_js_1.harmonicWallCost; } });
Object.defineProperty(exports, "generateInitialPosition", { enumerable: true, get: function () { return types_js_1.generateInitialPosition; } });
Object.defineProperty(exports, "calculateBFTQuorum", { enumerable: true, get: function () { return types_js_1.calculateBFTQuorum; } });
// Lifecycle
var lifecycle_js_1 = require("./lifecycle.js");
Object.defineProperty(exports, "AgentManager", { enumerable: true, get: function () { return lifecycle_js_1.AgentManager; } });
Object.defineProperty(exports, "AgentMonitor", { enumerable: true, get: function () { return lifecycle_js_1.AgentMonitor; } });
Object.defineProperty(exports, "isAgentDead", { enumerable: true, get: function () { return lifecycle_js_1.isAgentDead; } });
Object.defineProperty(exports, "createAgentManager", { enumerable: true, get: function () { return lifecycle_js_1.createAgentManager; } });
Object.defineProperty(exports, "createAgentConfig", { enumerable: true, get: function () { return lifecycle_js_1.createAgentConfig; } });
// Swarm
var swarm_js_1 = require("./swarm.js");
// Constants
Object.defineProperty(exports, "MIN_COHERENCE_THRESHOLD", { enumerable: true, get: function () { return swarm_js_1.MIN_COHERENCE_THRESHOLD; } });
Object.defineProperty(exports, "MAX_HYPERBOLIC_DISTANCE", { enumerable: true, get: function () { return swarm_js_1.MAX_HYPERBOLIC_DISTANCE; } });
Object.defineProperty(exports, "ROGUE_QUARANTINE_THRESHOLD", { enumerable: true, get: function () { return swarm_js_1.ROGUE_QUARANTINE_THRESHOLD; } });
// Hyperbolic operations
Object.defineProperty(exports, "mobiusAdd", { enumerable: true, get: function () { return swarm_js_1.mobiusAdd; } });
Object.defineProperty(exports, "mobiusScale", { enumerable: true, get: function () { return swarm_js_1.mobiusScale; } });
Object.defineProperty(exports, "hyperbolicCentroid", { enumerable: true, get: function () { return swarm_js_1.hyperbolicCentroid; } });
// Formation
Object.defineProperty(exports, "generateRingFormation", { enumerable: true, get: function () { return swarm_js_1.generateRingFormation; } });
Object.defineProperty(exports, "generateDispersedFormation", { enumerable: true, get: function () { return swarm_js_1.generateDispersedFormation; } });
Object.defineProperty(exports, "generateConvergentFormation", { enumerable: true, get: function () { return swarm_js_1.generateConvergentFormation; } });
Object.defineProperty(exports, "createFormationTarget", { enumerable: true, get: function () { return swarm_js_1.createFormationTarget; } });
// Swarm coordinator
Object.defineProperty(exports, "SwarmCoordinator", { enumerable: true, get: function () { return swarm_js_1.SwarmCoordinator; } });
// BFT consensus
Object.defineProperty(exports, "collectVotes", { enumerable: true, get: function () { return swarm_js_1.collectVotes; } });
Object.defineProperty(exports, "weightedVoteCount", { enumerable: true, get: function () { return swarm_js_1.weightedVoteCount; } });
Object.defineProperty(exports, "runWeightedConsensus", { enumerable: true, get: function () { return swarm_js_1.runWeightedConsensus; } });
// Rogue detection
Object.defineProperty(exports, "detectRogueAgent", { enumerable: true, get: function () { return swarm_js_1.detectRogueAgent; } });
Object.defineProperty(exports, "quarantineAgent", { enumerable: true, get: function () { return swarm_js_1.quarantineAgent; } });
// Kafka
var kafka_js_1 = require("./kafka.js");
// Topic naming
Object.defineProperty(exports, "getTopicName", { enumerable: true, get: function () { return kafka_js_1.getTopicName; } });
Object.defineProperty(exports, "getTierTopicPattern", { enumerable: true, get: function () { return kafka_js_1.getTierTopicPattern; } });
Object.defineProperty(exports, "getAgentTopics", { enumerable: true, get: function () { return kafka_js_1.getAgentTopics; } });
Object.defineProperty(exports, "parseTopicName", { enumerable: true, get: function () { return kafka_js_1.parseTopicName; } });
// Mock client (for testing)
Object.defineProperty(exports, "MockKafkaClient", { enumerable: true, get: function () { return kafka_js_1.MockKafkaClient; } });
// Event publishing
Object.defineProperty(exports, "AgentEventPublisher", { enumerable: true, get: function () { return kafka_js_1.AgentEventPublisher; } });
Object.defineProperty(exports, "AgentEventSubscriber", { enumerable: true, get: function () { return kafka_js_1.AgentEventSubscriber; } });
// Factory functions
Object.defineProperty(exports, "createKafkaClient", { enumerable: true, get: function () { return kafka_js_1.createKafkaClient; } });
Object.defineProperty(exports, "createEventPublisher", { enumerable: true, get: function () { return kafka_js_1.createEventPublisher; } });
Object.defineProperty(exports, "createEventSubscriber", { enumerable: true, get: function () { return kafka_js_1.createEventSubscriber; } });
//# sourceMappingURL=index.js.map