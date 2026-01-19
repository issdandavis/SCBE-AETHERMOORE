import { anyArbitraryBuilder } from './_internals/builders/AnyArbitraryBuilder.js';
import { toQualifiedObjectConstraints } from './_internals/helpers/QualifiedObjectConstraints.js';
/**@__NO_SIDE_EFFECTS__*/function anything(constraints) {
    return anyArbitraryBuilder(toQualifiedObjectConstraints(constraints));
}
export { anything };
