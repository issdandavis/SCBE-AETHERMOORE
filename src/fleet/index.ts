/**
 * @file index.ts
 * @module fleet
 * @component Fleet Management System
 * @version 3.0.0
 * @since 2026-01-20
 *
 * SCBE Fleet Module - Distributed agent orchestration with Redis/BullMQ
 *
 * Exports:
 * - FleetOrchestrator  - Main orchestrator class
 * - AgentRole          - Agent role type (captain, architect, etc.)
 * - FleetTask          - Task interface
 * - TaskResult         - Result interface
 * - FleetConfig        - Configuration options
 *
 * Usage:
 * ```typescript
 * import { FleetOrchestrator } from '@scbe/fleet';
 *
 * const fleet = new FleetOrchestrator({
 *   redisUrl: 'redis://localhost:6379',
 *   maxConcurrency: 10
 * });
 *
 * await fleet.submitTask({
 *   type: 'implement',
 *   payload: { feature: 'new-feature' },
 *   priority: 'high'
 * });
 * ```
 */

export * from './redis-orchestrator.js';
