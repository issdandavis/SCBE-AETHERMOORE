import { jsonValue } from './jsonValue.js';
const safeJsonStringify = JSON.stringify;
export /**@__NO_SIDE_EFFECTS__*/function json(constraints = {}) {
    const arb = jsonValue(constraints);
    return arb.map(safeJsonStringify);
}
