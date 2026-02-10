/**
 * @file systems.ts
 * @module fleet/polly-pads/modes/systems
 * @layer L13
 * @component Systems Mode - Power & Sensor Monitoring
 * @version 1.0.0
 */
import { BaseMode } from './base-mode';
import { ModeActionResult } from './types';
/**
 * Systems specialist mode.
 *
 * Handles power management, sensor health monitoring, and subsystem telemetry.
 * Critical for autonomous operation where power budgets are strict.
 */
export declare class SystemsMode extends BaseMode {
    constructor();
    protected onActivate(): void;
    protected onDeactivate(): void;
    protected doExecuteAction(action: string, params: Record<string, unknown>): ModeActionResult;
    private checkPower;
    private sensorHealth;
    private systemStatus;
    private allocatePower;
}
//# sourceMappingURL=systems.d.ts.map