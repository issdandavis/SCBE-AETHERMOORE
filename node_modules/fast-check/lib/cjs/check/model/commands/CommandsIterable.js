"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.CommandsIterable = void 0;
const symbols_js_1 = require("../../symbols.js");
class CommandsIterable {
    constructor(commands, metadataForReplay) {
        this.commands = commands;
        this.metadataForReplay = metadataForReplay;
        this[symbols_js_1.cloneMethod] = function () {
            return new CommandsIterable(this.commands.map((c) => c.clone()), this.metadataForReplay);
        };
    }
    [Symbol.iterator]() {
        return this.commands[Symbol.iterator]();
    }
    toString() {
        const serializedCommands = this.commands
            .filter((c) => c.hasRan)
            .map((c) => c.toString())
            .join(',');
        const metadata = this.metadataForReplay();
        return metadata.length !== 0 ? `${serializedCommands} /*${metadata}*/` : serializedCommands;
    }
}
exports.CommandsIterable = CommandsIterable;
