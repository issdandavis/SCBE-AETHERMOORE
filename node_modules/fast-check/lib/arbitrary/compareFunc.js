import { buildCompareFunctionArbitrary } from './_internals/builders/CompareFunctionArbitraryBuilder.js';
const safeObjectAssign = Object.assign;
export /**@__NO_SIDE_EFFECTS__*/function compareFunc() {
    return buildCompareFunctionArbitrary(safeObjectAssign((hA, hB) => hA - hB, {
        toString() {
            return '(hA, hB) => hA - hB';
        },
    }));
}
