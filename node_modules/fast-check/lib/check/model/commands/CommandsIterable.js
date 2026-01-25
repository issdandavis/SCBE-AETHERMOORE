import { cloneMethod } from '../../symbols.js';
export class CommandsIterable {
    constructor(commands, metadataForReplay) {
        this.commands = commands;
        this.metadataForReplay = metadataForReplay;
        this[cloneMethod] = function () {
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
