import { spawn as nodeSpawn, spawnSync as nodeSpawnSync } from 'node:child_process';

// Node's native spawn does not resolve .cmd launchers on Windows. cross-spawn
// preserves argv boundaries while resolving npm/global command shims, avoiding
// shell:true and its command-injection surface.
const crossSpawn: typeof nodeSpawn & { sync: typeof nodeSpawnSync } = require('cross-spawn');

export const spawn = crossSpawn;
export const spawnSync = crossSpawn.sync;
