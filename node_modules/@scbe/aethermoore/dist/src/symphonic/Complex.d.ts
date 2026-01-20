/**
 * SCBE Symphonic Cipher - Complex Number Class
 *
 * Represents a complex number (real + imaginary) with double-precision
 * floating point components. Essential for FFT calculations where
 * signal phases are manipulated.
 *
 * @module symphonic/Complex
 */
export declare class Complex {
    re: number;
    im: number;
    constructor(re: number, im: number);
    /**
     * Adds another complex number to this one.
     * (a + bi) + (c + di) = (a+c) + (b+d)i
     */
    add(other: Complex): Complex;
    /**
     * Subtracts another complex number from this one.
     * (a + bi) - (c + di) = (a-c) + (b-d)i
     */
    sub(other: Complex): Complex;
    /**
     * Multiplies this complex number by another.
     * (a + bi)(c + di) = (ac - bd) + (ad + bc)i
     */
    mul(other: Complex): Complex;
    /**
     * Divides this complex number by another.
     * (a + bi) / (c + di) = ((ac + bd) + (bc - ad)i) / (c² + d²)
     */
    div(other: Complex): Complex;
    /**
     * Returns the complex conjugate.
     * conj(a + bi) = a - bi
     */
    conjugate(): Complex;
    /**
     * Calculates the magnitude (absolute value/modulus) of the complex number.
     * |z| = sqrt(re² + im²)
     * This represents the 'amplitude' of the frequency component in the spectrum.
     */
    get magnitude(): number;
    /**
     * Calculates the squared magnitude (avoids sqrt for performance).
     * |z|² = re² + im²
     */
    get magnitudeSquared(): number;
    /**
     * Calculates the phase angle (argument) in radians.
     * arg(z) = atan2(im, re)
     */
    get phase(): number;
    /**
     * Scales the complex number by a real scalar.
     */
    scale(s: number): Complex;
    /**
     * Creates a Complex number from polar coordinates using Euler's formula.
     * e^(i*theta) = cos(theta) + i*sin(theta)
     * Used for generating Twiddle Factors in FFT.
     */
    static fromEuler(theta: number): Complex;
    /**
     * Creates a Complex number from polar form (magnitude and phase).
     * z = r * e^(i*theta) = r*cos(theta) + i*r*sin(theta)
     */
    static fromPolar(magnitude: number, phase: number): Complex;
    /**
     * Returns the zero complex number.
     */
    static zero(): Complex;
    /**
     * Returns the unit complex number (1 + 0i).
     */
    static one(): Complex;
    /**
     * Returns the imaginary unit (0 + 1i).
     */
    static i(): Complex;
    /**
     * Checks if two complex numbers are approximately equal.
     */
    equals(other: Complex, epsilon?: number): boolean;
    /**
     * Returns a string representation.
     */
    toString(): string;
    /**
     * Creates a deep copy of this complex number.
     */
    clone(): Complex;
}
//# sourceMappingURL=Complex.d.ts.map