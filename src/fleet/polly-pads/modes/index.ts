/**
 * @file index.ts
 * @module fleet/polly-pads/modes
 * @layer L13
 * @component Polly Pad Specialist Modes
 * @version 1.0.0
 *
 * Exports all 6 specialist modes and shared types.
 */

// Types
export * from './types';

// Base class
export { BaseMode } from './base-mode';

// Tech specialist modes
export { EngineeringMode } from './engineering';
export { NavigationMode } from './navigation';
export { SystemsMode } from './systems';

// Non-tech specialist modes
export { ScienceMode } from './science';
export { CommunicationsMode } from './communications';
export { MissionPlanningMode } from './mission-planning';

import { BaseMode } from './base-mode';
import { SpecialistMode } from './types';
import { EngineeringMode } from './engineering';
import { NavigationMode } from './navigation';
import { SystemsMode } from './systems';
import { ScienceMode } from './science';
import { CommunicationsMode } from './communications';
import { MissionPlanningMode } from './mission-planning';

/**
 * Factory: create a mode instance by name.
 */
export function createMode(mode: SpecialistMode): BaseMode {
  switch (mode) {
    case 'engineering':
      return new EngineeringMode();
    case 'navigation':
      return new NavigationMode();
    case 'systems':
      return new SystemsMode();
    case 'science':
      return new ScienceMode();
    case 'communications':
      return new CommunicationsMode();
    case 'mission_planning':
      return new MissionPlanningMode();
  }
}

/**
 * Create all 6 mode instances as a map.
 */
export function createAllModes(): Map<SpecialistMode, BaseMode> {
  const modes = new Map<SpecialistMode, BaseMode>();
  const modeNames: SpecialistMode[] = [
    'engineering',
    'navigation',
    'systems',
    'science',
    'communications',
    'mission_planning',
  ];
  for (const name of modeNames) {
    modes.set(name, createMode(name));
  }
  return modes;
}
