/**
 * @file communications.ts
 * @module fleet/polly-pads/modes/communications
 * @layer L13
 * @component Communications Mode - Liaison & Reporting
 * @version 1.0.0
 */
import { BaseMode } from './base-mode';
import { ModeActionResult } from './types';
/**
 * Communications specialist mode.
 *
 * Handles Earth sync, squad messaging, and status reporting.
 * Critical for maintaining contact and reporting decisions.
 */
export declare class CommunicationsMode extends BaseMode {
    constructor();
    protected onActivate(): void;
    protected onDeactivate(): void;
    protected doExecuteAction(action: string, params: Record<string, unknown>): ModeActionResult;
    private queueMessage;
    private sendStatus;
    private checkEarthContact;
    private broadcastSquad;
}
//# sourceMappingURL=communications.d.ts.map