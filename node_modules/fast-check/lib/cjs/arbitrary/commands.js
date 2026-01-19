"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.commands = commands;
const CommandsArbitrary_js_1 = require("./_internals/CommandsArbitrary.js");
const MaxLengthFromMinLength_js_1 = require("./_internals/helpers/MaxLengthFromMinLength.js");
/**@__NO_SIDE_EFFECTS__*/function commands(commandArbs, constraints = {}) {
    const { size, maxCommands = MaxLengthFromMinLength_js_1.MaxLengthUpperBound, disableReplayLog = false, replayPath = null } = constraints;
    const specifiedMaxCommands = constraints.maxCommands !== undefined;
    const maxGeneratedCommands = (0, MaxLengthFromMinLength_js_1.maxGeneratedLengthFromSizeForArbitrary)(size, 0, maxCommands, specifiedMaxCommands);
    return new CommandsArbitrary_js_1.CommandsArbitrary(commandArbs, maxGeneratedCommands, maxCommands, replayPath, disableReplayLog);
}
