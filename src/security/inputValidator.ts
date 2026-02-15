/**
 * @file inputValidator.ts
 * @module security/inputValidator
 * @layer Layer 1, Layer 3
 * @component Input Validation & Sanitization
 * @version 1.0.0
 *
 * Validates and sanitizes inputs before they enter the 14-layer security pipeline.
 * Enforces dimensional constraints, numerical bounds, and structural integrity
 * at the system boundary.
 */

/**
 * Validation result returned by all validators.
 */
export interface ValidationResult {
  valid: boolean;
  errors: string[];
  sanitized?: number[];
}

/**
 * Configuration for input validation.
 */
export interface ValidatorConfig {
  /** Maximum input dimension (default: 128) */
  maxDimension: number;
  /** Minimum input dimension (default: 2) */
  minDimension: number;
  /** Maximum absolute value for any component (default: 1e6) */
  maxAbsValue: number;
  /** Whether to clamp out-of-range values instead of rejecting (default: false) */
  clampOutOfRange: boolean;
  /** Maximum allowed NaN/Infinity ratio before rejection (default: 0) */
  maxNonFiniteRatio: number;
}

/**
 * Default validator configuration.
 */
export const DEFAULT_VALIDATOR_CONFIG: ValidatorConfig = {
  maxDimension: 128,
  minDimension: 2,
  maxAbsValue: 1e6,
  clampOutOfRange: false,
  maxNonFiniteRatio: 0,
};

/**
 * Validate and sanitize a numeric input vector for the security pipeline.
 *
 * Checks:
 * - Input is a non-empty array of numbers
 * - Dimension is within configured bounds
 * - No NaN/Infinity values (unless maxNonFiniteRatio > 0)
 * - Magnitudes are within bounds
 *
 * @param input - Raw input vector
 * @param config - Validation configuration
 * @returns Validation result with optional sanitized output
 */
export function validateInput(
  input: unknown,
  config: Partial<ValidatorConfig> = {}
): ValidationResult {
  const cfg = { ...DEFAULT_VALIDATOR_CONFIG, ...config };
  const errors: string[] = [];

  // Type check
  if (!Array.isArray(input)) {
    return { valid: false, errors: ['Input must be an array'] };
  }

  if (input.length === 0) {
    return { valid: false, errors: ['Input must be non-empty'] };
  }

  // Dimension check
  if (input.length < cfg.minDimension) {
    errors.push(`Input dimension ${input.length} below minimum ${cfg.minDimension}`);
  }

  if (input.length > cfg.maxDimension) {
    errors.push(`Input dimension ${input.length} exceeds maximum ${cfg.maxDimension}`);
  }

  if (errors.length > 0) {
    return { valid: false, errors };
  }

  // Numeric type check
  for (let i = 0; i < input.length; i++) {
    if (typeof input[i] !== 'number') {
      errors.push(`Element at index ${i} is not a number (got ${typeof input[i]})`);
    }
  }

  if (errors.length > 0) {
    return { valid: false, errors };
  }

  const numInput = input as number[];

  // Non-finite check
  const nonFiniteCount = numInput.filter((v) => !Number.isFinite(v)).length;
  const nonFiniteRatio = nonFiniteCount / numInput.length;

  if (nonFiniteRatio > cfg.maxNonFiniteRatio) {
    if (cfg.maxNonFiniteRatio === 0 && nonFiniteCount > 0) {
      errors.push(`Input contains ${nonFiniteCount} non-finite value(s) (NaN or Infinity)`);
    } else {
      errors.push(
        `Non-finite ratio ${nonFiniteRatio.toFixed(3)} exceeds limit ${cfg.maxNonFiniteRatio}`
      );
    }
  }

  // Magnitude check
  const sanitized: number[] = [];
  for (let i = 0; i < numInput.length; i++) {
    const v = numInput[i];
    if (!Number.isFinite(v)) {
      sanitized.push(0);
    } else if (Math.abs(v) > cfg.maxAbsValue) {
      if (cfg.clampOutOfRange) {
        sanitized.push(Math.sign(v) * cfg.maxAbsValue);
      } else {
        errors.push(
          `Element at index ${i} exceeds magnitude limit: |${v}| > ${cfg.maxAbsValue}`
        );
        sanitized.push(v);
      }
    } else {
      sanitized.push(v);
    }
  }

  if (errors.length > 0) {
    return { valid: false, errors };
  }

  return { valid: true, errors: [], sanitized };
}

/**
 * Validate that a dimension D is suitable for the 6D Sacred Tongues metric.
 * The SCBE pipeline canonical dimension is D=6 (one per Sacred Tongue).
 *
 * @param inputLength - Length of the input vector
 * @param D - Target dimension (default: 6)
 * @returns Whether the input length is compatible
 */
export function validateSacredTongueDimension(inputLength: number, D: number = 6): boolean {
  // Pipeline expects at least 2*D elements (amplitudes + phases)
  return inputLength >= 2 * D;
}

/**
 * Pad or truncate an input vector to match the expected pipeline dimension.
 *
 * @param input - Input vector
 * @param targetLength - Target length (2*D for the pipeline)
 * @returns Padded/truncated vector
 */
export function normalizeInputLength(input: number[], targetLength: number): number[] {
  if (input.length === targetLength) {
    return input;
  }

  if (input.length > targetLength) {
    return input.slice(0, targetLength);
  }

  // Pad with zeros
  const padded = new Array(targetLength).fill(0);
  for (let i = 0; i < input.length; i++) {
    padded[i] = input[i];
  }
  return padded;
}
