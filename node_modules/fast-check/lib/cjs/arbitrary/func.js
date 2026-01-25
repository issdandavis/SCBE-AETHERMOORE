"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.func = func;
const hash_js_1 = require("../utils/hash.js");
const stringify_js_1 = require("../utils/stringify.js");
const symbols_js_1 = require("../check/symbols.js");
const array_js_1 = require("./array.js");
const integer_js_1 = require("./integer.js");
const noShrink_js_1 = require("./noShrink.js");
const tuple_js_1 = require("./tuple.js");
const TextEscaper_js_1 = require("./_internals/helpers/TextEscaper.js");
const globals_js_1 = require("../utils/globals.js");
const safeObjectDefineProperties = Object.defineProperties;
const safeObjectKeys = Object.keys;
/**@__NO_SIDE_EFFECTS__*/function func(arb) {
    return (0, tuple_js_1.tuple)((0, array_js_1.array)(arb, { minLength: 1 }), (0, noShrink_js_1.noShrink)((0, integer_js_1.integer)())).map(([outs, seed]) => {
        const producer = () => {
            const recorded = {};
            const f = (...args) => {
                const repr = (0, stringify_js_1.stringify)(args);
                const val = outs[(0, hash_js_1.hash)(`${seed}${repr}`) % outs.length];
                recorded[repr] = val;
                return (0, symbols_js_1.hasCloneMethod)(val) ? val[symbols_js_1.cloneMethod]() : val;
            };
            function prettyPrint(stringifiedOuts) {
                const seenValues = (0, globals_js_1.safeMap)((0, globals_js_1.safeMap)((0, globals_js_1.safeSort)(safeObjectKeys(recorded)), (k) => `${k} => ${(0, stringify_js_1.stringify)(recorded[k])}`), (line) => `/* ${(0, TextEscaper_js_1.escapeForMultilineComments)(line)} */`);
                return `function(...args) {
  // With hash and stringify coming from fast-check${seenValues.length !== 0 ? `\n  ${seenValues.join('\n  ')}` : ''}
  const outs = ${stringifiedOuts};
  return outs[hash('${seed}' + stringify(args)) % outs.length];
}`;
            }
            return safeObjectDefineProperties(f, {
                toString: { value: () => prettyPrint((0, stringify_js_1.stringify)(outs)) },
                [stringify_js_1.toStringMethod]: { value: () => prettyPrint((0, stringify_js_1.stringify)(outs)) },
                [stringify_js_1.asyncToStringMethod]: { value: async () => prettyPrint(await (0, stringify_js_1.asyncStringify)(outs)) },
                [symbols_js_1.cloneMethod]: { value: producer, configurable: true },
            });
        };
        return producer();
    });
}
