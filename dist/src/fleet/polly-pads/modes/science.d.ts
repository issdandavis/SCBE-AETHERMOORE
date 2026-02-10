/**
 * @file science.ts
 * @module fleet/polly-pads/modes/science
 * @layer L13
 * @component Science Mode - Analysis & Discovery
 * @version 1.0.0
 */
import { BaseMode } from './base-mode';
import { ModeActionResult } from './types';
/**
 * Science specialist mode.
 *
 * Handles sample analysis, data interpretation, and hypothesis testing.
 * Primary mode during normal science operations (e.g., Mars sample collection).
 */
export declare class ScienceMode extends BaseMode {
    constructor();
    protected onActivate(): void;
    protected onDeactivate(): void;
    protected doExecuteAction(action: string, params: Record<string, unknown>): ModeActionResult;
    private collectSample;
    private analyzeSample;
    private testHypothesis;
    private interpretData;
}
//# sourceMappingURL=science.d.ts.map