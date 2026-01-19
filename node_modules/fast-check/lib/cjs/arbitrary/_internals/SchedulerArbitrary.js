"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SchedulerArbitrary = void 0;
const Arbitrary_js_1 = require("../../check/arbitrary/definition/Arbitrary.js");
const Value_js_1 = require("../../check/arbitrary/definition/Value.js");
const Stream_js_1 = require("../../stream/Stream.js");
const SchedulerImplem_js_1 = require("./implementations/SchedulerImplem.js");
function buildNextTaskIndex(mrng) {
    const clonedMrng = mrng.clone();
    return {
        clone: () => buildNextTaskIndex(clonedMrng),
        nextTaskIndex: (scheduledTasks) => {
            return mrng.nextInt(0, scheduledTasks.length - 1);
        },
    };
}
class SchedulerArbitrary extends Arbitrary_js_1.Arbitrary {
    constructor(act) {
        super();
        this.act = act;
    }
    generate(mrng, _biasFactor) {
        return new Value_js_1.Value(new SchedulerImplem_js_1.SchedulerImplem(this.act, buildNextTaskIndex(mrng.clone())), undefined);
    }
    canShrinkWithoutContext(value) {
        return false;
    }
    shrink(_value, _context) {
        return Stream_js_1.Stream.nil();
    }
}
exports.SchedulerArbitrary = SchedulerArbitrary;
