import type {
  DecisionResult,
  EnforcementRequest,
  OfflineRuntime,
} from './offline_mode.js';
import { DECIDE } from './offline_mode.js';

export type {
  DecisionResult,
  EnforcementRequest,
  GovernanceScalars,
  OfflineRuntime,
} from './offline_mode.js';

export function governanceDecide(
  request: EnforcementRequest,
  runtime: OfflineRuntime,
): DecisionResult {
  return DECIDE(request, runtime);
}

