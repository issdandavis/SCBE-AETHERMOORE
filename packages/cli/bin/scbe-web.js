#!/usr/bin/env node
'use strict';

const { runWebCommand } = require('../lib/agent-web-server');

runWebCommand(process.argv.slice(2)).catch((error) => {
  process.stderr.write(`scbe web: ${error.message || error}\n`);
  process.exitCode = 1;
});
