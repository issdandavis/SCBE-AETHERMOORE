/**
 * @file mission-planning.ts
 * @module fleet/polly-pads/modes/mission-planning
 * @layer L13
 * @component Mission Planning Mode - Strategy & Validation
 * @version 1.0.0
 */
import { BaseMode } from './base-mode';
import { ModeActionResult } from './types';
/**
 * Mission Planning specialist mode.
 *
 * Handles risk assessment, objective prioritization, and decision validation.
 * The "strategic brain" that validates proposals from other modes.
 */
export declare class MissionPlanningMode extends BaseMode {
    constructor();
    protected onActivate(): void;
    protected onDeactivate(): void;
    protected doExecuteAction(action: string, params: Record<string, unknown>): ModeActionResult;
    private assessRisk;
    private prioritizeObjectives;
    private validateDecision;
    private updateTimeline;
}
//# sourceMappingURL=mission-planning.d.ts.map