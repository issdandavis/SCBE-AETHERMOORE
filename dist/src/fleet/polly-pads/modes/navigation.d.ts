/**
 * @file navigation.ts
 * @module fleet/polly-pads/modes/navigation
 * @layer L13
 * @component Navigation Mode - Pathfinding & Terrain
 * @version 1.0.0
 */
import { BaseMode } from './base-mode';
import { ModeActionResult } from './types';
/**
 * Navigation specialist mode.
 *
 * Handles route planning, obstacle avoidance, and terrain analysis.
 * Uses path algorithms (A*, Dijkstra) and SLAM for localization.
 */
export declare class NavigationMode extends BaseMode {
    constructor();
    protected onActivate(): void;
    protected onDeactivate(): void;
    protected doExecuteAction(action: string, params: Record<string, unknown>): ModeActionResult;
    private planRoute;
    private analyzeTerrain;
    private detectObstacles;
    private updatePosition;
}
//# sourceMappingURL=navigation.d.ts.map