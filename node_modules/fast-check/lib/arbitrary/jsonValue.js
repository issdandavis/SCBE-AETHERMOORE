import { string } from './string.js';
import { jsonConstraintsBuilder } from './_internals/helpers/JsonConstraintsBuilder.js';
import { anything } from './anything.js';
export /**@__NO_SIDE_EFFECTS__*/function jsonValue(constraints = {}) {
    const noUnicodeString = constraints.noUnicodeString === undefined || constraints.noUnicodeString === true;
    const stringArbitrary = 'stringUnit' in constraints
        ? string({ unit: constraints.stringUnit })
        : noUnicodeString
            ? string()
            : string({ unit: 'binary' });
    return anything(jsonConstraintsBuilder(stringArbitrary, constraints));
}
