"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.LazyArbitrary = void 0;
const Arbitrary_js_1 = require("../../check/arbitrary/definition/Arbitrary.js");
class LazyArbitrary extends Arbitrary_js_1.Arbitrary {
    constructor(name) {
        super();
        this.name = name;
        this.underlying = null;
    }
    generate(mrng, biasFactor) {
        if (this.underlying === null) {
            throw new Error(`Lazy arbitrary ${JSON.stringify(this.name)} not correctly initialized`);
        }
        return this.underlying.generate(mrng, biasFactor);
    }
    canShrinkWithoutContext(value) {
        if (this.underlying === null) {
            throw new Error(`Lazy arbitrary ${JSON.stringify(this.name)} not correctly initialized`);
        }
        return this.underlying.canShrinkWithoutContext(value);
    }
    shrink(value, context) {
        if (this.underlying === null) {
            throw new Error(`Lazy arbitrary ${JSON.stringify(this.name)} not correctly initialized`);
        }
        return this.underlying.shrink(value, context);
    }
}
exports.LazyArbitrary = LazyArbitrary;
