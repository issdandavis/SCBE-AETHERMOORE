import { escapeForTemplateString } from '../helpers/TextEscaper.js';
import { cloneMethod } from '../../../check/symbols.js';
import { stringify } from '../../../utils/stringify.js';
const defaultSchedulerAct = (f) => f();
export const numTicksBeforeScheduling = 50;
export class SchedulerImplem {
    constructor(act, taskSelector) {
        this.act = act;
        this.taskSelector = taskSelector;
        this.lastTaskId = 0;
        this.sourceTaskSelector = taskSelector.clone();
        this.scheduledTasks = [];
        this.triggeredTasks = [];
        this.scheduledWatchers = [];
        this[cloneMethod] = function () {
            return new SchedulerImplem(this.act, this.sourceTaskSelector);
        };
    }
    static buildLog(reportItem) {
        return `[task\${${reportItem.taskId}}] ${reportItem.label.length !== 0 ? `${reportItem.schedulingType}::${reportItem.label}` : reportItem.schedulingType} ${reportItem.status}${reportItem.outputValue !== undefined ? ` with value ${escapeForTemplateString(reportItem.outputValue)}` : ''}`;
    }
    log(schedulingType, taskId, label, metadata, status, data) {
        this.triggeredTasks.push({
            status,
            schedulingType,
            taskId,
            label,
            metadata,
            outputValue: data !== undefined ? stringify(data) : undefined,
        });
    }
    scheduleInternal(schedulingType, label, task, metadata, customAct, thenTaskToBeAwaited) {
        const taskId = ++this.lastTaskId;
        let trigger = undefined;
        const scheduledPromise = new Promise((resolve, reject) => {
            trigger = () => {
                const promise = Promise.resolve(thenTaskToBeAwaited !== undefined ? task.then(() => thenTaskToBeAwaited()) : task);
                promise.then((data) => {
                    this.log(schedulingType, taskId, label, metadata, 'resolved', data);
                    resolve(data);
                }, (err) => {
                    this.log(schedulingType, taskId, label, metadata, 'rejected', err);
                    reject(err);
                });
                return promise;
            };
        });
        this.scheduledTasks.push({
            original: task,
            trigger: trigger,
            schedulingType,
            taskId,
            label,
            metadata,
            customAct,
        });
        if (this.scheduledWatchers.length !== 0) {
            this.scheduledWatchers[0]();
        }
        return scheduledPromise;
    }
    schedule(task, label, metadata, customAct) {
        return this.scheduleInternal('promise', label || '', task, metadata, customAct || defaultSchedulerAct);
    }
    scheduleFunction(asyncFunction, customAct) {
        return (...args) => this.scheduleInternal('function', `${asyncFunction.name}(${args.map(stringify).join(',')})`, asyncFunction(...args), undefined, customAct || defaultSchedulerAct);
    }
    scheduleSequence(sequenceBuilders, customAct) {
        const status = { done: false, faulty: false };
        const dummyResolvedPromise = { then: (f) => f() };
        let resolveSequenceTask = () => { };
        const sequenceTask = new Promise((resolve) => {
            resolveSequenceTask = () => resolve({ done: status.done, faulty: status.faulty });
        });
        const onFaultyItemNoThrow = () => {
            status.faulty = true;
            resolveSequenceTask();
        };
        const onDone = () => {
            status.done = true;
            resolveSequenceTask();
        };
        const registerNextBuilder = (index, previous) => {
            if (index >= sequenceBuilders.length) {
                previous.then(onDone, onFaultyItemNoThrow);
                return;
            }
            previous.then(() => {
                const item = sequenceBuilders[index];
                const [builder, label, metadata] = typeof item === 'function' ? [item, item.name, undefined] : [item.builder, item.label, item.metadata];
                const scheduled = this.scheduleInternal('sequence', label, dummyResolvedPromise, metadata, customAct || defaultSchedulerAct, () => builder());
                registerNextBuilder(index + 1, scheduled);
            }, onFaultyItemNoThrow);
        };
        registerNextBuilder(0, dummyResolvedPromise);
        return Object.assign(status, { task: sequenceTask });
    }
    count() {
        return this.scheduledTasks.length;
    }
    internalWaitOne() {
        if (this.scheduledTasks.length === 0) {
            throw new Error('No task scheduled');
        }
        const taskIndex = this.taskSelector.nextTaskIndex(this.scheduledTasks);
        const [scheduledTask] = this.scheduledTasks.splice(taskIndex, 1);
        return scheduledTask.customAct(() => {
            const scheduled = scheduledTask.trigger();
            return scheduled.catch((_err) => {
            });
        });
    }
    waitOne(customAct) {
        const waitAct = customAct || defaultSchedulerAct;
        const waitOneResult = this.act(() => waitAct(() => this.internalWaitOne()));
        return waitOneResult;
    }
    async waitAll(customAct) {
        while (this.scheduledTasks.length > 0) {
            await this.waitOne(customAct);
        }
    }
    async internalWaitFor(unscheduledTask, options) {
        let taskResolved = false;
        const customAct = options.customAct;
        const onWaitStart = options.onWaitStart;
        const onWaitIdle = options.onWaitIdle;
        const launchAwaiterOnInit = options.launchAwaiterOnInit;
        let resolveFinal = undefined;
        let rejectFinal = undefined;
        let awaiterTicks = 0;
        let awaiterPromise = null;
        let awaiterScheduledTaskPromise = null;
        const awaiter = async () => {
            awaiterTicks = numTicksBeforeScheduling;
            for (awaiterTicks = numTicksBeforeScheduling; !taskResolved && awaiterTicks > 0; --awaiterTicks) {
                await Promise.resolve();
            }
            if (!taskResolved && this.scheduledTasks.length > 0) {
                if (onWaitStart !== undefined) {
                    onWaitStart();
                }
                awaiterScheduledTaskPromise = this.waitOne(customAct);
                return awaiterScheduledTaskPromise.then(() => {
                    awaiterScheduledTaskPromise = null;
                    return awaiter();
                }, (err) => {
                    awaiterScheduledTaskPromise = null;
                    taskResolved = true;
                    rejectFinal(err);
                    throw err;
                });
            }
            if (!taskResolved && onWaitIdle !== undefined) {
                onWaitIdle();
            }
            awaiterPromise = null;
        };
        const handleNotified = () => {
            if (awaiterPromise !== null) {
                awaiterTicks = numTicksBeforeScheduling + 1;
                return;
            }
            awaiterPromise = awaiter().catch(() => { });
        };
        const clearAndReplaceWatcher = () => {
            const handleNotifiedIndex = this.scheduledWatchers.indexOf(handleNotified);
            if (handleNotifiedIndex !== -1) {
                this.scheduledWatchers.splice(handleNotifiedIndex, 1);
            }
            if (handleNotifiedIndex === 0 && this.scheduledWatchers.length !== 0) {
                this.scheduledWatchers[0]();
            }
        };
        const finalTask = new Promise((resolve, reject) => {
            resolveFinal = (value) => {
                clearAndReplaceWatcher();
                resolve(value);
            };
            rejectFinal = (error) => {
                clearAndReplaceWatcher();
                reject(error);
            };
        });
        unscheduledTask.then((ret) => {
            taskResolved = true;
            if (awaiterScheduledTaskPromise === null) {
                resolveFinal(ret);
            }
            else {
                awaiterScheduledTaskPromise.then(() => resolveFinal(ret), (error) => rejectFinal(error));
            }
        }, (err) => {
            taskResolved = true;
            if (awaiterScheduledTaskPromise === null) {
                rejectFinal(err);
            }
            else {
                awaiterScheduledTaskPromise.then(() => rejectFinal(err), () => rejectFinal(err));
            }
        });
        if ((this.scheduledTasks.length > 0 || launchAwaiterOnInit) && this.scheduledWatchers.length === 0) {
            handleNotified();
        }
        this.scheduledWatchers.push(handleNotified);
        return finalTask;
    }
    waitNext(count, customAct) {
        let resolver = undefined;
        let remaining = count;
        const awaited = remaining <= 0
            ? Promise.resolve()
            : new Promise((r) => {
                resolver = () => {
                    if (--remaining <= 0) {
                        r();
                    }
                };
            });
        return this.internalWaitFor(awaited, {
            customAct,
            onWaitStart: resolver,
            onWaitIdle: undefined,
            launchAwaiterOnInit: false,
        });
    }
    waitIdle(customAct) {
        let resolver = undefined;
        const awaited = new Promise((r) => (resolver = r));
        return this.internalWaitFor(awaited, {
            customAct,
            onWaitStart: undefined,
            onWaitIdle: resolver,
            launchAwaiterOnInit: true,
        });
    }
    waitFor(unscheduledTask, customAct) {
        return this.internalWaitFor(unscheduledTask, {
            customAct,
            onWaitStart: undefined,
            onWaitIdle: undefined,
            launchAwaiterOnInit: false,
        });
    }
    report() {
        return [
            ...this.triggeredTasks,
            ...this.scheduledTasks.map((t) => ({
                status: 'pending',
                schedulingType: t.schedulingType,
                taskId: t.taskId,
                label: t.label,
                metadata: t.metadata,
            })),
        ];
    }
    toString() {
        return ('schedulerFor()`\n' +
            this.report()
                .map(SchedulerImplem.buildLog)
                .map((log) => `-> ${log}`)
                .join('\n') +
            '`');
    }
}
