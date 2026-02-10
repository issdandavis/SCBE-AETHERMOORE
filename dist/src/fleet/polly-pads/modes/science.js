"use strict";
/**
 * @file science.ts
 * @module fleet/polly-pads/modes/science
 * @layer L13
 * @component Science Mode - Analysis & Discovery
 * @version 1.0.0
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.ScienceMode = void 0;
const base_mode_1 = require("./base-mode");
/**
 * Science specialist mode.
 *
 * Handles sample analysis, data interpretation, and hypothesis testing.
 * Primary mode during normal science operations (e.g., Mars sample collection).
 */
class ScienceMode extends base_mode_1.BaseMode {
    constructor() {
        super('science');
    }
    onActivate() {
        if (!this.stateData.samples) {
            this.stateData.samples = [];
        }
        if (!this.stateData.hypotheses) {
            this.stateData.hypotheses = [];
        }
    }
    onDeactivate() {
        // Persist sample data and hypotheses
    }
    doExecuteAction(action, params) {
        switch (action) {
            case 'collect_sample':
                return this.collectSample(params);
            case 'analyze_sample':
                return this.analyzeSample(params);
            case 'test_hypothesis':
                return this.testHypothesis(params);
            case 'interpret_data':
                return this.interpretData(params);
            default:
                return {
                    success: false,
                    action,
                    data: {},
                    timestamp: Date.now(),
                    confidence: 0,
                    error: `Unknown science action: ${action}`,
                };
        }
    }
    collectSample(params) {
        const location = params.location || 'unknown';
        const samples = this.stateData.samples;
        const sample = {
            id: `SAMPLE-${Date.now().toString(36).toUpperCase()}`,
            location,
            collectedAt: Date.now(),
            type: params.type || 'soil',
            status: 'collected',
        };
        samples.push(sample);
        return {
            success: true,
            action: 'collect_sample',
            data: sample,
            timestamp: Date.now(),
            confidence: 0.95,
        };
    }
    analyzeSample(params) {
        const sampleId = params.sampleId;
        const samples = this.stateData.samples;
        const sample = samples.find((s) => s.id === sampleId);
        if (!sample) {
            return {
                success: false,
                action: 'analyze_sample',
                data: {},
                timestamp: Date.now(),
                confidence: 0,
                error: `Sample ${sampleId} not found`,
            };
        }
        sample.status = 'analyzed';
        const analysis = {
            sampleId,
            composition: {
                silicon: 0.45,
                iron: 0.18,
                aluminum: 0.08,
                calcium: 0.06,
                other: 0.23,
            },
            anomalies: [],
            quality: 0.92,
        };
        return {
            success: true,
            action: 'analyze_sample',
            data: analysis,
            timestamp: Date.now(),
            confidence: 0.88,
        };
    }
    testHypothesis(params) {
        const hypothesis = params.hypothesis || 'unknown';
        const hypotheses = this.stateData.hypotheses;
        const result = {
            hypothesis,
            tested: true,
            supported: Math.random() > 0.3,
            pValue: Math.random() * 0.1,
            testedAt: Date.now(),
        };
        hypotheses.push(result);
        return {
            success: true,
            action: 'test_hypothesis',
            data: result,
            timestamp: Date.now(),
            confidence: 0.75,
        };
    }
    interpretData(params) {
        const datasetId = params.datasetId || 'latest';
        return {
            success: true,
            action: 'interpret_data',
            data: {
                datasetId,
                patterns: ['periodic_variation', 'spatial_correlation'],
                significance: 0.82,
                recommendation: 'further_investigation',
            },
            timestamp: Date.now(),
            confidence: 0.78,
        };
    }
}
exports.ScienceMode = ScienceMode;
//# sourceMappingURL=science.js.map