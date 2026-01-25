"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.shrinkBigInt = shrinkBigInt;
const Stream_js_1 = require("../../../stream/Stream.js");
const Value_js_1 = require("../../../check/arbitrary/definition/Value.js");
const globals_js_1 = require("../../../utils/globals.js");
function halveBigInt(n) {
    return n / (0, globals_js_1.BigInt)(2);
}
function shrinkBigInt(current, target, tryTargetAsap) {
    const realGap = current - target;
    function* shrinkDecr() {
        let previous = tryTargetAsap ? undefined : target;
        const gap = tryTargetAsap ? realGap : halveBigInt(realGap);
        for (let toremove = gap; toremove > 0; toremove = halveBigInt(toremove)) {
            const next = current - toremove;
            yield new Value_js_1.Value(next, previous);
            previous = next;
        }
    }
    function* shrinkIncr() {
        let previous = tryTargetAsap ? undefined : target;
        const gap = tryTargetAsap ? realGap : halveBigInt(realGap);
        for (let toremove = gap; toremove < 0; toremove = halveBigInt(toremove)) {
            const next = current - toremove;
            yield new Value_js_1.Value(next, previous);
            previous = next;
        }
    }
    return realGap > 0 ? (0, Stream_js_1.stream)(shrinkDecr()) : (0, Stream_js_1.stream)(shrinkIncr());
}
