#!/usr/bin/env bash
set -euo pipefail

echo "[1/5] package metadata"
node -e "const p=require('./package.json'); if(!p.name||!p.version){throw new Error('missing name/version')} console.log('name='+p.name,'version='+p.version)"

echo "[2/5] build preflight (non-blocking diagnostics)"
if npm run build >/tmp/npm-build.log 2>&1; then
  echo "build: OK"
else
  echo "build: FAILED (diagnostic only in this check)"
  echo "--- build log tail ---"
  tail -n 25 /tmp/npm-build.log || true
  echo "----------------------"
fi

echo "[3/5] tarball dry-run"
npm pack --dry-run --json >/tmp/npm-pack.json
node -e "const x=require('/tmp/npm-pack.json')[0]; console.log('tarball='+x.filename,'entries='+x.entryCount,'size='+x.size)"

echo "[4/5] npm auth status"
if npm whoami >/dev/null 2>&1; then
  echo "npm auth: OK"
else
  echo "npm auth: NOT LOGGED IN (publish will fail until authenticated)"
fi

echo "[5/5] version availability"
PKG=$(node -p "require('./package.json').name")
VER=$(node -p "require('./package.json').version")
if npm view "$PKG@$VER" version >/dev/null 2>&1; then
  echo "version check: $PKG@$VER already exists on npm"
else
  echo "version check: $PKG@$VER available for publish"
fi

echo "publish preflight complete"
