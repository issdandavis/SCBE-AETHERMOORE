import { Error } from '../../utils/globals.js';
const timeoutAfter = (timeMs, setTimeoutSafe, clearTimeoutSafe) => {
    let timeoutHandle = null;
    const promise = new Promise((resolve) => {
        timeoutHandle = setTimeoutSafe(() => {
            resolve({ error: new Error(`Property timeout: exceeded limit of ${timeMs} milliseconds`) });
        }, timeMs);
    });
    return {
        clear: () => clearTimeoutSafe(timeoutHandle),
        promise,
    };
};
export class TimeoutProperty {
    constructor(property, timeMs, setTimeoutSafe, clearTimeoutSafe) {
        this.property = property;
        this.timeMs = timeMs;
        this.setTimeoutSafe = setTimeoutSafe;
        this.clearTimeoutSafe = clearTimeoutSafe;
    }
    isAsync() {
        return true;
    }
    generate(mrng, runId) {
        return this.property.generate(mrng, runId);
    }
    shrink(value) {
        return this.property.shrink(value);
    }
    async run(v) {
        const t = timeoutAfter(this.timeMs, this.setTimeoutSafe, this.clearTimeoutSafe);
        const propRun = Promise.race([this.property.run(v), t.promise]);
        propRun.then(t.clear, t.clear);
        return propRun;
    }
    runBeforeEach() {
        return Promise.resolve(this.property.runBeforeEach());
    }
    runAfterEach() {
        return Promise.resolve(this.property.runAfterEach());
    }
}
