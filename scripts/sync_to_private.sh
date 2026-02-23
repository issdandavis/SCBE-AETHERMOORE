#!/usr/bin/env bash
# =============================================================================
# sync_to_private.sh
# Syncs private/proprietary content from SCBE-AETHERMOORE to SCBE-private repo.
#
# Usage:
#   cd /c/Users/issda/SCBE_Production_Pack_local
#   bash scripts/sync_to_private.sh
#
# What it syncs:
#   training-data/  -> SCBE-private/training-data/
#   training/       -> SCBE-private/training/
#   audio files     -> SCBE-private/audio/
#
# What it EXCLUDES:
#   node_modules/, __pycache__/, .git/, *.pyc, .pytest_cache/
# =============================================================================

set -euo pipefail

# --- Configuration -----------------------------------------------------------
PUBLIC_REPO="/c/Users/issda/SCBE_Production_Pack_local"
PRIVATE_REPO="/c/Users/issda/SCBE-private"

# Directories to sync (relative to PUBLIC_REPO)
SYNC_DIRS=(
    "training-data"
    "training"
)

# rsync exclude patterns
EXCLUDES=(
    "--exclude=node_modules/"
    "--exclude=__pycache__/"
    "--exclude=.git/"
    "--exclude=.pytest_cache/"
    "--exclude=.mypy_cache/"
    "--exclude=.hypothesis/"
    "--exclude=*.pyc"
    "--exclude=*.pyo"
    "--exclude=.env"
    "--exclude=.env.*"
)

# --- Preflight checks --------------------------------------------------------
if [ ! -d "$PUBLIC_REPO" ]; then
    echo "ERROR: Public repo not found at $PUBLIC_REPO"
    exit 1
fi

if [ ! -d "$PRIVATE_REPO" ]; then
    echo "ERROR: Private repo not found at $PRIVATE_REPO"
    echo "       Run: mkdir -p $PRIVATE_REPO && cd $PRIVATE_REPO && git init"
    exit 1
fi

# --- Check for rsync ---------------------------------------------------------
if command -v rsync &>/dev/null; then
    USE_RSYNC=true
else
    USE_RSYNC=false
    echo "WARNING: rsync not found, falling back to cp -r (no incremental sync)"
fi

# --- Sync function -----------------------------------------------------------
sync_dir() {
    local src="$1"
    local dest="$2"

    if [ ! -d "$src" ]; then
        echo "  SKIP: $src (directory not found)"
        return
    fi

    echo "  SYNC: $src -> $dest"

    if $USE_RSYNC; then
        rsync -av --delete "${EXCLUDES[@]}" "$src/" "$dest/"
    else
        # Fallback: remove destination, copy fresh (excluding patterns manually)
        mkdir -p "$dest"
        # Use find + cp, skipping excluded dirs
        cd "$src"
        find . -type f \
            ! -path "*/node_modules/*" \
            ! -path "*/__pycache__/*" \
            ! -path "*/.git/*" \
            ! -path "*/.pytest_cache/*" \
            ! -path "*/.mypy_cache/*" \
            ! -path "*/.hypothesis/*" \
            ! -name "*.pyc" \
            ! -name "*.pyo" \
            ! -name ".env" \
            -exec bash -c 'mkdir -p "'"$dest"'/$(dirname "{}")" && cp "{}" "'"$dest"'/{}"' \;
        cd "$PUBLIC_REPO"
    fi
}

# --- Main sync ---------------------------------------------------------------
echo "============================================="
echo "  SCBE Private Repo Sync"
echo "  $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "============================================="
echo ""
echo "Source:      $PUBLIC_REPO"
echo "Destination: $PRIVATE_REPO"
echo ""

# Sync main directories
for dir in "${SYNC_DIRS[@]}"; do
    sync_dir "$PUBLIC_REPO/$dir" "$PRIVATE_REPO/$dir"
done

# Sync audio files (WAV/MP3) to dedicated audio/ directory
echo ""
echo "--- Audio files ---"
AUDIO_SRC="$PUBLIC_REPO/training-data/audio"
AUDIO_DEST="$PRIVATE_REPO/audio"

if [ -d "$AUDIO_SRC" ]; then
    echo "  SYNC: $AUDIO_SRC -> $AUDIO_DEST"
    mkdir -p "$AUDIO_DEST"
    if $USE_RSYNC; then
        rsync -av "$AUDIO_SRC/" "$AUDIO_DEST/"
    else
        cp -r "$AUDIO_SRC/"* "$AUDIO_DEST/" 2>/dev/null || true
    fi
else
    echo "  SKIP: $AUDIO_SRC (not found)"
fi

# --- Summary -----------------------------------------------------------------
echo ""
echo "============================================="
echo "  Sync complete."
echo ""
echo "  Next steps:"
echo "    cd $PRIVATE_REPO"
echo "    git add -A"
echo "    git status"
echo "    git commit -m 'Sync training data from public repo'"
echo "    git push origin main"
echo "============================================="
