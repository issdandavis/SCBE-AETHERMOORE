"use strict";
/**
 * @file systems.ts
 * @module fleet/polly-pads/modes/systems
 * @layer L13
 * @component Systems Mode - Power & Sensor Monitoring
 * @version 1.0.0
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.SystemsMode = void 0;
const base_mode_1 = require("./base-mode");
/**
 * Systems specialist mode.
 *
 * Handles power management, sensor health monitoring, and subsystem telemetry.
 * Critical for autonomous operation where power budgets are strict.
 */
class SystemsMode extends base_mode_1.BaseMode {
    constructor() {
        super('systems');
    }
    onActivate() {
        if (!this.stateData.telemetrySnapshots) {
            this.stateData.telemetrySnapshots = [];
        }
        if (!this.stateData.powerBudget) {
            this.stateData.powerBudget = { totalWh: 1000, usedWh: 0, reserveWh: 200 };
        }
    }
    onDeactivate() {
        // Persist telemetry state
    }
    doExecuteAction(action, params) {
        switch (action) {
            case 'check_power':
                return this.checkPower(params);
            case 'sensor_health':
                return this.sensorHealth(params);
            case 'system_status':
                return this.systemStatus(params);
            case 'allocate_power':
                return this.allocatePower(params);
            default:
                return {
                    success: false,
                    action,
                    data: {},
                    timestamp: Date.now(),
                    confidence: 0,
                    error: `Unknown systems action: ${action}`,
                };
        }
    }
    checkPower(params) {
        const budget = this.stateData.powerBudget;
        const available = budget.totalWh - budget.usedWh;
        const reserveOk = available > budget.reserveWh;
        return {
            success: true,
            action: 'check_power',
            data: {
                totalWh: budget.totalWh,
                usedWh: budget.usedWh,
                availableWh: available,
                reserveWh: budget.reserveWh,
                reserveOk,
                estimatedRemainingHours: available / 50,
            },
            timestamp: Date.now(),
            confidence: 0.95,
        };
    }
    sensorHealth(params) {
        const sensorId = params.sensorId || 'all';
        const sensors = [
            { id: 'cam_front', status: 'healthy', calibration: 0.98 },
            { id: 'cam_rear', status: 'healthy', calibration: 0.95 },
            { id: 'spectrometer', status: 'healthy', calibration: 0.97 },
            { id: 'temperature', status: 'healthy', calibration: 0.99 },
            { id: 'pressure', status: 'degraded', calibration: 0.82 },
        ];
        const result = sensorId === 'all' ? sensors : sensors.filter((s) => s.id === sensorId);
        return {
            success: true,
            action: 'sensor_health',
            data: { sensors: result, overallHealth: 0.94 },
            timestamp: Date.now(),
            confidence: 0.92,
        };
    }
    systemStatus(params) {
        return {
            success: true,
            action: 'system_status',
            data: {
                cpu: { usage: 0.45, temperature: 62 },
                memory: { usedMB: 2048, totalMB: 4096 },
                storage: { usedGB: 32, totalGB: 64 },
                network: { meshActive: true, earthContact: false },
                uptime: Date.now() - (this.stateData.bootTime || Date.now() - 86400000),
            },
            timestamp: Date.now(),
            confidence: 0.98,
        };
    }
    allocatePower(params) {
        const subsystem = params.subsystem || 'unknown';
        const watts = params.watts || 10;
        const budget = this.stateData.powerBudget;
        const available = budget.totalWh - budget.usedWh - budget.reserveWh;
        if (watts > available) {
            return {
                success: false,
                action: 'allocate_power',
                data: { subsystem, requested: watts, available },
                timestamp: Date.now(),
                confidence: 0.95,
                error: `Insufficient power: ${watts}W requested, ${available}W available`,
            };
        }
        budget.usedWh += watts;
        return {
            success: true,
            action: 'allocate_power',
            data: { subsystem, allocated: watts, remainingWh: budget.totalWh - budget.usedWh },
            timestamp: Date.now(),
            confidence: 0.95,
        };
    }
}
exports.SystemsMode = SystemsMode;
//# sourceMappingURL=systems.js.map