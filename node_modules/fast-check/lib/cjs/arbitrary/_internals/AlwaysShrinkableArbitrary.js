"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.AlwaysShrinkableArbitrary = void 0;
const Arbitrary_js_1 = require("../../check/arbitrary/definition/Arbitrary.js");
const Stream_js_1 = require("../../stream/Stream.js");
const NoUndefinedAsContext_js_1 = require("./helpers/NoUndefinedAsContext.js");
class AlwaysShrinkableArbitrary extends Arbitrary_js_1.Arbitrary {
    constructor(arb) {
        super();
        this.arb = arb;
    }
    generate(mrng, biasFactor) {
        const value = this.arb.generate(mrng, biasFactor);
        return (0, NoUndefinedAsContext_js_1.noUndefinedAsContext)(value);
    }
    canShrinkWithoutContext(value) {
        return true;
    }
    shrink(value, context) {
        if (context === undefined && !this.arb.canShrinkWithoutContext(value)) {
            return Stream_js_1.Stream.nil();
        }
        const safeContext = context !== NoUndefinedAsContext_js_1.UndefinedContextPlaceholder ? context : undefined;
        return this.arb.shrink(value, safeContext).map(NoUndefinedAsContext_js_1.noUndefinedAsContext);
    }
}
exports.AlwaysShrinkableArbitrary = AlwaysShrinkableArbitrary;
