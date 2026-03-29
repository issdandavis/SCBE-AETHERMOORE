#!/usr/bin/env bash
# post-push-gitlab.sh
# -------------------
# Mirrors the most recent push to the GitLab remote.
#
# Git does not have a native "post-push" hook. This script is designed to be
# called manually or via a git alias after pushing to GitHub:
#
#   git config alias.pushall \
#     '!f() { git push origin "$@" && bash scripts/git-hooks/post-push-gitlab.sh "$@"; }; f'
#
#   git pushall main
#   git pushall fix/my-branch
#
# It can also be invoked directly:
#   bash scripts/git-hooks/post-push-gitlab.sh main
#   bash scripts/git-hooks/post-push-gitlab.sh          # uses current branch

set -euo pipefail

GITLAB_REMOTE="gitlab"

# Determine branch
if [ $# -ge 1 ]; then
    BRANCH="$1"
else
    BRANCH=$(git rev-parse --abbrev-ref HEAD)
fi

echo "[post-push-gitlab] Mirroring ${BRANCH} to ${GITLAB_REMOTE}..."

# Attempt push
if git push "${GITLAB_REMOTE}" "${BRANCH}" 2>&1; then
    echo "[post-push-gitlab] Success: ${BRANCH} pushed to ${GITLAB_REMOTE}"
else
    EXIT_CODE=$?
    echo "[post-push-gitlab] Warning: push to ${GITLAB_REMOTE} failed (exit ${EXIT_CODE})"
    echo "[post-push-gitlab] You may need to run: python scripts/system/dual_sync.py --sync --create-pr-if-blocked"
    # Don't fail the overall push -- this is advisory
    exit 0
fi
