import { array } from './array.js';
import { createSlicesForString } from './_internals/helpers/SlicesForStringBuilder.js';
import { stringUnit } from './_internals/StringUnitArbitrary.js';
import { patternsToStringMapper, patternsToStringUnmapperFor } from './_internals/mappers/PatternsToString.js';
function extractUnitArbitrary(constraints) {
    if (typeof constraints.unit === 'object') {
        return constraints.unit;
    }
    switch (constraints.unit) {
        case 'grapheme':
            return stringUnit('grapheme', 'full');
        case 'grapheme-composite':
            return stringUnit('composite', 'full');
        case 'grapheme-ascii':
        case undefined:
            return stringUnit('grapheme', 'ascii');
        case 'binary':
            return stringUnit('binary', 'full');
        case 'binary-ascii':
            return stringUnit('binary', 'ascii');
    }
}
export /**@__NO_SIDE_EFFECTS__*/function string(constraints = {}) {
    const charArbitrary = extractUnitArbitrary(constraints);
    const unmapper = patternsToStringUnmapperFor(charArbitrary, constraints);
    const experimentalCustomSlices = createSlicesForString(charArbitrary, constraints);
    const enrichedConstraints = { ...constraints, experimentalCustomSlices };
    return array(charArbitrary, enrichedConstraints).map(patternsToStringMapper, unmapper);
}
