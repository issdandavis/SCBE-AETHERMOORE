"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.QualifiedParameters = void 0;
const pure_rand_1 = require("pure-rand");
const VerbosityLevel_js_1 = require("./VerbosityLevel.js");
const safeDateNow = Date.now;
const safeMathMin = Math.min;
const safeMathRandom = Math.random;
class QualifiedParameters {
    constructor(op) {
        const p = op || {};
        this.seed = QualifiedParameters.readSeed(p);
        this.randomType = QualifiedParameters.readRandomType(p);
        this.numRuns = QualifiedParameters.readNumRuns(p);
        this.verbose = QualifiedParameters.readVerbose(p);
        this.maxSkipsPerRun = p.maxSkipsPerRun !== undefined ? p.maxSkipsPerRun : 100;
        this.timeout = QualifiedParameters.safeTimeout(p.timeout);
        this.skipAllAfterTimeLimit = QualifiedParameters.safeTimeout(p.skipAllAfterTimeLimit);
        this.interruptAfterTimeLimit = QualifiedParameters.safeTimeout(p.interruptAfterTimeLimit);
        this.markInterruptAsFailure = p.markInterruptAsFailure === true;
        this.skipEqualValues = p.skipEqualValues === true;
        this.ignoreEqualValues = p.ignoreEqualValues === true;
        this.logger =
            p.logger !== undefined
                ? p.logger
                : (v) => {
                    console.log(v);
                };
        this.path = p.path !== undefined ? p.path : '';
        this.unbiased = p.unbiased === true;
        this.examples = p.examples !== undefined ? p.examples : [];
        this.endOnFailure = p.endOnFailure === true;
        this.reporter = p.reporter;
        this.asyncReporter = p.asyncReporter;
        this.includeErrorInReport = p.includeErrorInReport === true;
    }
    toParameters() {
        const parameters = {
            seed: this.seed,
            randomType: this.randomType,
            numRuns: this.numRuns,
            maxSkipsPerRun: this.maxSkipsPerRun,
            timeout: this.timeout,
            skipAllAfterTimeLimit: this.skipAllAfterTimeLimit,
            interruptAfterTimeLimit: this.interruptAfterTimeLimit,
            markInterruptAsFailure: this.markInterruptAsFailure,
            skipEqualValues: this.skipEqualValues,
            ignoreEqualValues: this.ignoreEqualValues,
            path: this.path,
            logger: this.logger,
            unbiased: this.unbiased,
            verbose: this.verbose,
            examples: this.examples,
            endOnFailure: this.endOnFailure,
            reporter: this.reporter,
            asyncReporter: this.asyncReporter,
            includeErrorInReport: this.includeErrorInReport,
        };
        return parameters;
    }
    static read(op) {
        return new QualifiedParameters(op);
    }
}
exports.QualifiedParameters = QualifiedParameters;
QualifiedParameters.createQualifiedRandomGenerator = (random) => {
    return (seed) => {
        const rng = random(seed);
        if (rng.unsafeJump === undefined) {
            rng.unsafeJump = () => (0, pure_rand_1.unsafeSkipN)(rng, 42);
        }
        return rng;
    };
};
QualifiedParameters.readSeed = (p) => {
    if (p.seed === undefined)
        return safeDateNow() ^ (safeMathRandom() * 0x100000000);
    const seed32 = p.seed | 0;
    if (p.seed === seed32)
        return seed32;
    const gap = p.seed - seed32;
    return seed32 ^ (gap * 0x100000000);
};
QualifiedParameters.readRandomType = (p) => {
    if (p.randomType === undefined)
        return pure_rand_1.default.xorshift128plus;
    if (typeof p.randomType === 'string') {
        switch (p.randomType) {
            case 'mersenne':
                return QualifiedParameters.createQualifiedRandomGenerator(pure_rand_1.default.mersenne);
            case 'congruential':
            case 'congruential32':
                return QualifiedParameters.createQualifiedRandomGenerator(pure_rand_1.default.congruential32);
            case 'xorshift128plus':
                return pure_rand_1.default.xorshift128plus;
            case 'xoroshiro128plus':
                return pure_rand_1.default.xoroshiro128plus;
            default:
                throw new Error(`Invalid random specified: '${p.randomType}'`);
        }
    }
    const mrng = p.randomType(0);
    if ('min' in mrng && mrng.min !== -0x80000000) {
        throw new Error(`Invalid random number generator: min must equal -0x80000000, got ${String(mrng.min)}`);
    }
    if ('max' in mrng && mrng.max !== 0x7fffffff) {
        throw new Error(`Invalid random number generator: max must equal 0x7fffffff, got ${String(mrng.max)}`);
    }
    if ('unsafeJump' in mrng) {
        return p.randomType;
    }
    return QualifiedParameters.createQualifiedRandomGenerator(p.randomType);
};
QualifiedParameters.readNumRuns = (p) => {
    const defaultValue = 100;
    if (p.numRuns !== undefined)
        return p.numRuns;
    if (p.num_runs !== undefined)
        return p.num_runs;
    return defaultValue;
};
QualifiedParameters.readVerbose = (p) => {
    if (p.verbose === undefined)
        return VerbosityLevel_js_1.VerbosityLevel.None;
    if (typeof p.verbose === 'boolean') {
        return p.verbose === true ? VerbosityLevel_js_1.VerbosityLevel.Verbose : VerbosityLevel_js_1.VerbosityLevel.None;
    }
    if (p.verbose <= VerbosityLevel_js_1.VerbosityLevel.None) {
        return VerbosityLevel_js_1.VerbosityLevel.None;
    }
    if (p.verbose >= VerbosityLevel_js_1.VerbosityLevel.VeryVerbose) {
        return VerbosityLevel_js_1.VerbosityLevel.VeryVerbose;
    }
    return p.verbose | 0;
};
QualifiedParameters.safeTimeout = (value) => {
    if (value === undefined) {
        return undefined;
    }
    return safeMathMin(value, 0x7fffffff);
};
