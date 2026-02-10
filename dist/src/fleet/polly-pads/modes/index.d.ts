/**
 * @file index.ts
 * @module fleet/polly-pads/modes
 * @layer L13
 * @component Polly Pad Specialist Modes
 * @version 1.0.0
 *
 * Exports all 6 specialist modes and shared types.
 */
export * from './types';
export { BaseMode } from './base-mode';
export { EngineeringMode } from './engineering';
export { NavigationMode } from './navigation';
export { SystemsMode } from './systems';
export { ScienceMode } from './science';
export { CommunicationsMode } from './communications';
export { MissionPlanningMode } from './mission-planning';
import { BaseMode } from './base-mode';
import { SpecialistMode } from './types';
/**
 * Factory: create a mode instance by name.
 */
export declare function createMode(mode: SpecialistMode): BaseMode;
/**
 * Create all 6 mode instances as a map.
 */
export declare function createAllModes(): Map<SpecialistMode, BaseMode>;
//# sourceMappingURL=index.d.ts.map