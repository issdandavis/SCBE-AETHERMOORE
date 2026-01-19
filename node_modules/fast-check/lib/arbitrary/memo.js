import { safeHasOwnProperty } from '../utils/globals.js';
let contextRemainingDepth = 10;
export /**@__NO_SIDE_EFFECTS__*/function memo(builder) {
    const previous = {};
    return ((maxDepth) => {
        const n = maxDepth !== undefined ? maxDepth : contextRemainingDepth;
        if (!safeHasOwnProperty(previous, n)) {
            const prev = contextRemainingDepth;
            contextRemainingDepth = n - 1;
            previous[n] = builder(n);
            contextRemainingDepth = prev;
        }
        return previous[n];
    });
}
