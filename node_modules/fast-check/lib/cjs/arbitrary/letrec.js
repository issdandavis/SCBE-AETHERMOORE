"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.letrec = letrec;
const LazyArbitrary_js_1 = require("./_internals/LazyArbitrary.js");
const globals_js_1 = require("../utils/globals.js");
const safeGetOwnPropertyNames = Object.getOwnPropertyNames;
function createLazyArbsPool() {
    const lazyArbsPool = new globals_js_1.Map();
    const getLazyFromPool = (key) => {
        let lazyArb = (0, globals_js_1.safeMapGet)(lazyArbsPool, key);
        if (lazyArb !== undefined) {
            return lazyArb;
        }
        lazyArb = new LazyArbitrary_js_1.LazyArbitrary(String(key));
        (0, globals_js_1.safeMapSet)(lazyArbsPool, key, lazyArb);
        return lazyArb;
    };
    return getLazyFromPool;
}
/**@__NO_SIDE_EFFECTS__*/function letrec(builder) {
    const getLazyFromPool = createLazyArbsPool();
    const strictArbs = builder(getLazyFromPool);
    const declaredArbitraryNames = safeGetOwnPropertyNames(strictArbs);
    for (const name of declaredArbitraryNames) {
        const lazyArb = getLazyFromPool(name);
        lazyArb.underlying = strictArbs[name];
    }
    return strictArbs;
}
