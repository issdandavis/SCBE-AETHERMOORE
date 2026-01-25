"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.buildCompareFunctionArbitrary = buildCompareFunctionArbitrary;
const TextEscaper_js_1 = require("../helpers/TextEscaper.js");
const symbols_js_1 = require("../../../check/symbols.js");
const hash_js_1 = require("../../../utils/hash.js");
const stringify_js_1 = require("../../../utils/stringify.js");
const integer_js_1 = require("../../integer.js");
const noShrink_js_1 = require("../../noShrink.js");
const tuple_js_1 = require("../../tuple.js");
const globals_js_1 = require("../../../utils/globals.js");
const safeObjectAssign = Object.assign;
const safeObjectKeys = Object.keys;
function buildCompareFunctionArbitrary(cmp) {
    return (0, tuple_js_1.tuple)((0, noShrink_js_1.noShrink)((0, integer_js_1.integer)()), (0, noShrink_js_1.noShrink)((0, integer_js_1.integer)({ min: 1, max: 0xffffffff }))).map(([seed, hashEnvSize]) => {
        const producer = () => {
            const recorded = {};
            const f = (a, b) => {
                const reprA = (0, stringify_js_1.stringify)(a);
                const reprB = (0, stringify_js_1.stringify)(b);
                const hA = (0, hash_js_1.hash)(`${seed}${reprA}`) % hashEnvSize;
                const hB = (0, hash_js_1.hash)(`${seed}${reprB}`) % hashEnvSize;
                const val = cmp(hA, hB);
                recorded[`[${reprA},${reprB}]`] = val;
                return val;
            };
            return safeObjectAssign(f, {
                toString: () => {
                    const seenValues = safeObjectKeys(recorded)
                        .sort()
                        .map((k) => `${k} => ${(0, stringify_js_1.stringify)(recorded[k])}`)
                        .map((line) => `/* ${(0, TextEscaper_js_1.escapeForMultilineComments)(line)} */`);
                    return `function(a, b) {
  // With hash and stringify coming from fast-check${seenValues.length !== 0 ? `\n  ${(0, globals_js_1.safeJoin)(seenValues, '\n  ')}` : ''}
  const cmp = ${cmp};
  const hA = hash('${seed}' + stringify(a)) % ${hashEnvSize};
  const hB = hash('${seed}' + stringify(b)) % ${hashEnvSize};
  return cmp(hA, hB);
}`;
                },
                [symbols_js_1.cloneMethod]: producer,
            });
        };
        return producer();
    });
}
