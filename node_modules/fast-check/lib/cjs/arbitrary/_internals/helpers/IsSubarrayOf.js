"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.isSubarrayOf = isSubarrayOf;
const globals_js_1 = require("../../../utils/globals.js");
const safeObjectIs = Object.is;
function isSubarrayOf(source, small) {
    const countMap = new globals_js_1.Map();
    let countMinusZero = 0;
    for (const sourceEntry of source) {
        if (safeObjectIs(sourceEntry, -0)) {
            ++countMinusZero;
        }
        else {
            const oldCount = (0, globals_js_1.safeMapGet)(countMap, sourceEntry) || 0;
            (0, globals_js_1.safeMapSet)(countMap, sourceEntry, oldCount + 1);
        }
    }
    for (let index = 0; index !== small.length; ++index) {
        if (!(index in small)) {
            return false;
        }
        const smallEntry = small[index];
        if (safeObjectIs(smallEntry, -0)) {
            if (countMinusZero === 0)
                return false;
            --countMinusZero;
        }
        else {
            const oldCount = (0, globals_js_1.safeMapGet)(countMap, smallEntry) || 0;
            if (oldCount === 0)
                return false;
            (0, globals_js_1.safeMapSet)(countMap, smallEntry, oldCount - 1);
        }
    }
    return true;
}
