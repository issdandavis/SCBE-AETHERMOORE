import { getOrCreateAlphaNumericPercentArbitrary } from './_internals/builders/CharacterRangeArbitraryBuilder.js';
import { string } from './string.js';
export /**@__NO_SIDE_EFFECTS__*/function webSegment(constraints = {}) {
    return string({ unit: getOrCreateAlphaNumericPercentArbitrary("-._~!$&'()*+,;=:@"), size: constraints.size });
}
