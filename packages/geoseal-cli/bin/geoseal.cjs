#!/usr/bin/env node

const { spawnSync } = require("child_process");

function resolveTarget() {
  try {
    return require.resolve("scbe-aethermoore/bin/geoseal.cjs");
  } catch (error) {
    console.error(
      "geoseal-cli could not find scbe-aethermoore. Reinstall with: npm i geoseal-cli"
    );
    process.exit(1);
  }
}

const target = resolveTarget();
const child = spawnSync(process.execPath, [target, ...process.argv.slice(2)], {
  stdio: "inherit",
});

if (typeof child.status === "number") {
  process.exit(child.status);
}

process.exit(1);
