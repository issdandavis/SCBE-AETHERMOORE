/**
 * Workaround for Vite on Windows when `child_process.exec("net use", ...)`
 * is blocked by endpoint security / policies (throws spawn EPERM).
 *
 * Vite uses `net use` to map UNC network shares to drive letters for safe realpath.
 * In locked-down environments, spawning `net.exe` can be denied, which prevents
 * Vitest/Vite from even loading its config.
 *
 * This patch wraps the `exec("net use", ...)` call in a try/catch and falls back
 * to `fs.realpathSync.native` when it cannot spawn.
 *
 * NOTE: This script is intended to run as an npm `postinstall` step.
 */

const fs = require("node:fs");
const path = require("node:path");

function patchFile(filePath) {
  const src = fs.readFileSync(filePath, "utf8");

  const needle = 'exec("net use", (error, stdout) => {';
  if (!src.includes(needle)) {
    return { patched: false, reason: "needle_not_found" };
  }
  if (src.includes("SPAWN_EPERM_WORKAROUND")) {
    return { patched: false, reason: "already_patched" };
  }

  // Replace only the first occurrence of the exec call with the try-wrapped version,
  // and add a catch that falls back to native realpath.
  const patched = src.replace(
    needle,
    [
      "// SPAWN_EPERM_WORKAROUND: wrap net use exec to avoid spawn EPERM on locked-down Windows",
      "try {",
      needle,
    ].join("\n")
  );

  // Insert the catch block after the closing of the exec callback wiring.
  // We anchor on the exact line that ends the exec call in Vite's bundled code.
  const endAnchor = "});";
  const idx = patched.indexOf(needle);
  const afterExecIdx = patched.indexOf(endAnchor, idx);
  if (afterExecIdx === -1) {
    return { patched: false, reason: "end_anchor_not_found" };
  }

  const after = afterExecIdx + endAnchor.length;
  const finalSrc =
    patched.slice(0, after) +
    "\n} catch (e) {\n\t// If spawning `net use` is blocked (EPERM), fall back to native realpath.\n\tsafeRealpathSync = fs.realpathSync.native;\n}\n" +
    patched.slice(after);

  fs.writeFileSync(filePath, finalSrc, "utf8");
  return { patched: true };
}

function main() {
  if (process.platform !== "win32") return;

  const target = path.join(
    process.cwd(),
    "node_modules",
    "vite",
    "dist",
    "node",
    "chunks",
    "node.js"
  );
  if (!fs.existsSync(target)) return;

  const res = patchFile(target);
  if (res.patched) {
    // eslint-disable-next-line no-console
    console.log(`[scbe] Patched Vite windows safeRealpathSync: ${target}`);
  } else {
    // eslint-disable-next-line no-console
    console.log(`[scbe] Vite patch skipped (${res.reason}): ${target}`);
  }
}

main();

