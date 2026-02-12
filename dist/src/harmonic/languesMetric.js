"use strict";
/**
 * SCBE Langues Metric
 *
 * 6D phase-shifted exponential cost function with the Six Sacred Tongues.
 * L(x,t) = Σ wₗ exp(βₗ · (dₗ + sin(ωₗt + φₗ)))
 *
 * Tongues: KO, AV, RU, CA, UM, DR
 * Weights: wₗ = φˡ (golden ratio progression)
 * Phases: φₗ = 2πk/6 (60° intervals)
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.FluxingLanguesMetric = exports.LanguesMetric = exports.TONGUES = void 0;
exports.getFluxState = getFluxState;
/** Golden ratio φ = (1 + √5) / 2 */
const PHI = (1 + Math.sqrt(5)) / 2;
/** The Six Sacred Tongues */
exports.TONGUES = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
/**
 * Get the flux state name from ν value
 */
function getFluxState(nu) {
    if (nu >= 0.9)
        return 'Polly';
    if (nu >= 0.5)
        return 'Quasi';
    if (nu >= 0.1)
        return 'Demi';
    return 'Collapsed';
}
/**
 * Langues Metric - 6D governance cost function
 */
class LanguesMetric {
    betaBase;
    omegaBase;
    riskThresholds;
    /** Golden ratio weights wₗ = φˡ */
    weights;
    /** Phase offsets φₗ = 2πk/6 */
    phases;
    /** Beta values per tongue */
    betas;
    constructor(config = {}) {
        this.betaBase = config.betaBase ?? 1.0;
        this.omegaBase = config.omegaBase ?? 1.0;
        this.riskThresholds = config.riskThresholds ?? [1.0, 10.0];
        // Initialize weights: wₗ = φˡ
        this.weights = exports.TONGUES.map((_, i) => Math.pow(PHI, i));
        // Initialize phases: φₗ = 2πk/6 (60° intervals)
        this.phases = exports.TONGUES.map((_, i) => (2 * Math.PI * i) / 6);
        // Beta values scale with golden ratio
        this.betas = exports.TONGUES.map((_, i) => this.betaBase * Math.pow(PHI, i * 0.5));
    }
    /**
     * Compute Langues metric value
     * L(x,t) = Σ wₗ exp(βₗ · (dₗ + sin(ωₗt + φₗ)))
     *
     * @param point - 6D point (distances in each tongue dimension)
     * @param t - Time parameter
     * @returns Metric value
     */
    compute(point, t = 0) {
        let L = 0;
        for (let i = 0; i < 6; i++) {
            const d = point[i];
            const omega = this.omegaBase * (i + 1);
            const phase = this.phases[i];
            const sinTerm = Math.sin(omega * t + phase);
            const exponent = this.betas[i] * (d + sinTerm);
            L += this.weights[i] * Math.exp(exponent);
        }
        return L;
    }
    /**
     * Evaluate risk level and decision
     *
     * @param L - Langues metric value
     * @returns [risk, decision] tuple
     */
    riskLevel(L) {
        const [low, high] = this.riskThresholds;
        if (L < low)
            return [L, 'ALLOW'];
        if (L < high)
            return [L, 'QUARANTINE'];
        return [L, 'DENY'];
    }
    /**
     * Compute gradient ∂L/∂dₗ (for optimization)
     */
    gradient(point, t = 0) {
        const grad = [0, 0, 0, 0, 0, 0];
        for (let i = 0; i < 6; i++) {
            const d = point[i];
            const omega = this.omegaBase * (i + 1);
            const phase = this.phases[i];
            const sinTerm = Math.sin(omega * t + phase);
            const exponent = this.betas[i] * (d + sinTerm);
            // ∂L/∂dₗ = wₗ · βₗ · exp(βₗ · (dₗ + sin(...)))
            grad[i] = this.weights[i] * this.betas[i] * Math.exp(exponent);
        }
        return grad;
    }
}
exports.LanguesMetric = LanguesMetric;
/**
 * Fluxing Langues Metric - with dynamic dimension participation
 * L_f(x,t) = Σ νᵢ(t) wᵢ exp[βᵢ(dᵢ + sin(ωᵢt + φᵢ))]
 */
class FluxingLanguesMetric extends LanguesMetric {
    fluxes;
    constructor(config = {}, fluxes) {
        super(config);
        // Default flux configuration
        this.fluxes =
            fluxes ??
                exports.TONGUES.map((_, i) => ({
                    nu: 1.0,
                    nuBar: 0.8,
                    kappa: 0.1,
                    sigma: 0.05,
                    omega: 0.5 * (i + 1),
                }));
    }
    /**
     * Update flux values according to dynamics
     * ν̇ᵢ = κᵢ(ν̄ᵢ - νᵢ) + σᵢ sin(Ωᵢt)
     */
    updateFlux(t, dt) {
        for (const flux of this.fluxes) {
            const nuDot = flux.kappa * (flux.nuBar - flux.nu) + flux.sigma * Math.sin(flux.omega * t);
            flux.nu = Math.max(0, Math.min(1, flux.nu + nuDot * dt));
        }
    }
    /**
     * Get current flux values
     */
    getFluxValues() {
        return this.fluxes.map((f) => f.nu);
    }
    /**
     * Get flux states for all dimensions
     */
    getFluxStates() {
        return this.fluxes.map((f) => getFluxState(f.nu));
    }
    /**
     * Compute fluxing Langues metric
     * L_f(x,t) = Σ νᵢ(t) wᵢ exp[βᵢ(dᵢ + sin(ωᵢt + φᵢ))]
     */
    computeFluxing(point, t = 0) {
        let L = 0;
        for (let i = 0; i < 6; i++) {
            const nu = this.fluxes[i].nu;
            const d = point[i];
            const omega = this.omegaBase * (i + 1);
            const phase = this.phases[i];
            const sinTerm = Math.sin(omega * t + phase);
            const exponent = this.betas[i] * (d + sinTerm);
            L += nu * this.weights[i] * Math.exp(exponent);
        }
        return L;
    }
    /**
     * Effective dimensionality D_f = Σνᵢ
     */
    effectiveDimensionality() {
        return this.fluxes.reduce((sum, f) => sum + f.nu, 0);
    }
}
exports.FluxingLanguesMetric = FluxingLanguesMetric;
//# sourceMappingURL=languesMetric.js.map