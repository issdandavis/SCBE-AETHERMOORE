import { LazyArbitrary } from './_internals/LazyArbitrary.js';
import { Map as SMap, safeMapSet, safeMapGet } from '../utils/globals.js';
const safeGetOwnPropertyNames = Object.getOwnPropertyNames;
function createLazyArbsPool() {
    const lazyArbsPool = new SMap();
    const getLazyFromPool = (key) => {
        let lazyArb = safeMapGet(lazyArbsPool, key);
        if (lazyArb !== undefined) {
            return lazyArb;
        }
        lazyArb = new LazyArbitrary(String(key));
        safeMapSet(lazyArbsPool, key, lazyArb);
        return lazyArb;
    };
    return getLazyFromPool;
}
export /**@__NO_SIDE_EFFECTS__*/function letrec(builder) {
    const getLazyFromPool = createLazyArbsPool();
    const strictArbs = builder(getLazyFromPool);
    const declaredArbitraryNames = safeGetOwnPropertyNames(strictArbs);
    for (const name of declaredArbitraryNames) {
        const lazyArb = getLazyFromPool(name);
        lazyArb.underlying = strictArbs[name];
    }
    return strictArbs;
}
