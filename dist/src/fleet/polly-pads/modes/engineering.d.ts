/**
 * @file engineering.ts
 * @module fleet/polly-pads/modes/engineering
 * @layer L13
 * @component Engineering Mode - Repair & Diagnostics
 * @version 1.0.0
 */
import { BaseMode } from './base-mode';
import { ModeActionResult } from './types';
/**
 * Engineering specialist mode.
 *
 * Handles equipment repair, diagnostics, and maintenance.
 * Primary tech mode for hardware-related crisis response.
 */
export declare class EngineeringMode extends BaseMode {
    constructor();
    protected onActivate(): void;
    protected onDeactivate(): void;
    protected doExecuteAction(action: string, params: Record<string, unknown>): ModeActionResult;
    private diagnose;
    private generateRepairPlan;
    private executeRepair;
    private checkParts;
}
//# sourceMappingURL=engineering.d.ts.map