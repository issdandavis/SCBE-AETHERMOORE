#!/usr/bin/env node

const fs = require('fs/promises');
const path = require('path');
const { execSync } = require('child_process');

const PACKAGE_JSON_PATH = path.resolve(process.cwd(), 'package.json');
const BUMP_LEVELS = { patch: 0, minor: 1, major: 2 };

function parseSemver(version) {
  const match = /^(\d+)\.(\d+)\.(\d+)$/.exec(version);
  if (!match) {
    throw new Error(`Invalid semantic version in package.json: ${version}`);
  }

  return {
    major: Number(match[1]),
    minor: Number(match[2]),
    patch: Number(match[3])
  };
}

function bumpVersion(version, bumpType) {
  const parsed = parseSemver(version);

  if (bumpType === 'major') {
    return `${parsed.major + 1}.0.0`;
  }

  if (bumpType === 'minor') {
    return `${parsed.major}.${parsed.minor + 1}.0`;
  }

  return `${parsed.major}.${parsed.minor}.${parsed.patch + 1}`;
}

function runGit(command) {
  return execSync(command, { encoding: 'utf8' }).trim();
}

function getLastTag() {
  try {
    return runGit('git describe --tags --abbrev=0');
  } catch {
    return '';
  }
}

function getCommitMessagesSinceTag(lastTag) {
  const range = lastTag ? `${lastTag}..HEAD` : 'HEAD';
  try {
    const output = runGit(`git log ${range} --pretty=format:%B%n---END---`);
    return output
      .split('---END---')
      .map((message) => message.trim())
      .filter(Boolean);
  } catch {
    return [];
  }
}

function detectBumpType(messages) {
  let highestBump = 'patch';

  for (const message of messages) {
    const firstLine = message.split('\n')[0].trim();
    const hasBreaking = /BREAKING CHANGE:/i.test(message) || /!:/.test(firstLine);

    if (hasBreaking) {
      highestBump = 'major';
      break;
    }

    if (/^feat(\(.+\))?:\s+/i.test(firstLine) && BUMP_LEVELS.minor > BUMP_LEVELS[highestBump]) {
      highestBump = 'minor';
      continue;
    }

    if (/^fix(\(.+\))?:\s+/i.test(firstLine) && BUMP_LEVELS.patch > BUMP_LEVELS[highestBump]) {
      highestBump = 'patch';
    }
  }

  return highestBump;
}

async function main() {
  const raw = await fs.readFile(PACKAGE_JSON_PATH, 'utf8');
  const packageJson = JSON.parse(raw);
  const currentVersion = packageJson.version;

  if (!currentVersion) {
    throw new Error('package.json is missing a version field.');
  }

  const lastTag = getLastTag();
  const messages = getCommitMessagesSinceTag(lastTag);
  const bumpType = detectBumpType(messages);
  const nextVersion = bumpVersion(currentVersion, bumpType);

  packageJson.version = nextVersion;
  await fs.writeFile(PACKAGE_JSON_PATH, `${JSON.stringify(packageJson, null, 2)}\n`, 'utf8');

  process.stdout.write(
    JSON.stringify(
      {
        previousVersion: currentVersion,
        version: nextVersion,
        bumpType,
        lastTag: lastTag || null,
        analyzedCommits: messages.length
      },
      null,
      2
    )
  );
}

main().catch((error) => {
  console.error(`version-bump failed: ${error.message}`);
  process.exit(1);
});
