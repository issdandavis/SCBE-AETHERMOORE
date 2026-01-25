"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.buildSlicedGenerator = buildSlicedGenerator;
const NoopSlicedGenerator_js_1 = require("../implementations/NoopSlicedGenerator.js");
const SlicedBasedGenerator_js_1 = require("../implementations/SlicedBasedGenerator.js");
function buildSlicedGenerator(arb, mrng, slices, biasFactor) {
    if (biasFactor === undefined || slices.length === 0 || mrng.nextInt(1, biasFactor) !== 1) {
        return new NoopSlicedGenerator_js_1.NoopSlicedGenerator(arb, mrng, biasFactor);
    }
    return new SlicedBasedGenerator_js_1.SlicedBasedGenerator(arb, mrng, slices, biasFactor);
}
