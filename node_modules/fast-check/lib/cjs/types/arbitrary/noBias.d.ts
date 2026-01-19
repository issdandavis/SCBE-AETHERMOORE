import { Arbitrary } from '../check/arbitrary/definition/Arbitrary.js';
/**
 * Build an arbitrary without any bias.
 *
 * The produced instance wraps the source one and ensures the bias factor will always be passed to undefined meaning bias will be deactivated.
 * All the rest stays unchanged.
 *
 * @param arb - The original arbitrary used for generating values. This arbitrary remains unchanged.
 *
 * @remarks Since 3.20.0
 * @public
 */
export declare function noBias<T>(arb: Arbitrary<T>): Arbitrary<T>;
