"use strict";
/**
 * SCBE Symphonic Cipher - Complex Number Class
 *
 * Represents a complex number (real + imaginary) with double-precision
 * floating point components. Essential for FFT calculations where
 * signal phases are manipulated.
 *
 * @module symphonic/Complex
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.Complex = void 0;
class Complex {
    re;
    im;
    constructor(re, im) {
        this.re = re;
        this.im = im;
    }
    /**
     * Adds another complex number to this one.
     * (a + bi) + (c + di) = (a+c) + (b+d)i
     */
    add(other) {
        return new Complex(this.re + other.re, this.im + other.im);
    }
    /**
     * Subtracts another complex number from this one.
     * (a + bi) - (c + di) = (a-c) + (b-d)i
     */
    sub(other) {
        return new Complex(this.re - other.re, this.im - other.im);
    }
    /**
     * Multiplies this complex number by another.
     * (a + bi)(c + di) = (ac - bd) + (ad + bc)i
     */
    mul(other) {
        return new Complex(this.re * other.re - this.im * other.im, this.re * other.im + this.im * other.re);
    }
    /**
     * Divides this complex number by another.
     * (a + bi) / (c + di) = ((ac + bd) + (bc - ad)i) / (c² + d²)
     */
    div(other) {
        const denom = other.re * other.re + other.im * other.im;
        if (denom === 0) {
            throw new Error('Division by zero complex number');
        }
        return new Complex((this.re * other.re + this.im * other.im) / denom, (this.im * other.re - this.re * other.im) / denom);
    }
    /**
     * Returns the complex conjugate.
     * conj(a + bi) = a - bi
     */
    conjugate() {
        return new Complex(this.re, -this.im);
    }
    /**
     * Calculates the magnitude (absolute value/modulus) of the complex number.
     * |z| = sqrt(re² + im²)
     * This represents the 'amplitude' of the frequency component in the spectrum.
     */
    get magnitude() {
        return Math.sqrt(this.re * this.re + this.im * this.im);
    }
    /**
     * Calculates the squared magnitude (avoids sqrt for performance).
     * |z|² = re² + im²
     */
    get magnitudeSquared() {
        return this.re * this.re + this.im * this.im;
    }
    /**
     * Calculates the phase angle (argument) in radians.
     * arg(z) = atan2(im, re)
     */
    get phase() {
        return Math.atan2(this.im, this.re);
    }
    /**
     * Scales the complex number by a real scalar.
     */
    scale(s) {
        return new Complex(this.re * s, this.im * s);
    }
    /**
     * Creates a Complex number from polar coordinates using Euler's formula.
     * e^(i*theta) = cos(theta) + i*sin(theta)
     * Used for generating Twiddle Factors in FFT.
     */
    static fromEuler(theta) {
        return new Complex(Math.cos(theta), Math.sin(theta));
    }
    /**
     * Creates a Complex number from polar form (magnitude and phase).
     * z = r * e^(i*theta) = r*cos(theta) + i*r*sin(theta)
     */
    static fromPolar(magnitude, phase) {
        return new Complex(magnitude * Math.cos(phase), magnitude * Math.sin(phase));
    }
    /**
     * Returns the zero complex number.
     */
    static zero() {
        return new Complex(0, 0);
    }
    /**
     * Returns the unit complex number (1 + 0i).
     */
    static one() {
        return new Complex(1, 0);
    }
    /**
     * Returns the imaginary unit (0 + 1i).
     */
    static i() {
        return new Complex(0, 1);
    }
    /**
     * Checks if two complex numbers are approximately equal.
     */
    equals(other, epsilon = 1e-10) {
        return (Math.abs(this.re - other.re) < epsilon &&
            Math.abs(this.im - other.im) < epsilon);
    }
    /**
     * Returns a string representation.
     */
    toString() {
        if (this.im >= 0) {
            return `${this.re} + ${this.im}i`;
        }
        return `${this.re} - ${Math.abs(this.im)}i`;
    }
    /**
     * Creates a deep copy of this complex number.
     */
    clone() {
        return new Complex(this.re, this.im);
    }
}
exports.Complex = Complex;
//# sourceMappingURL=Complex.js.map