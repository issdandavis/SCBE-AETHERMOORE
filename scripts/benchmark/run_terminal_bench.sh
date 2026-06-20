#!/usr/bin/env bash
# Run terminal-bench from WSL2 against SCBE agent or any other agent.
# Must be run inside WSL2 (wsl -- bash scripts/benchmark/run_terminal_bench.sh).
#
# Usage:
#   AGENT=scbe TASKS=hello-world,fibonacci-server bash scripts/benchmark/run_terminal_bench.sh
#   AGENT=oracle TASKS=hello-world bash scripts/benchmark/run_terminal_bench.sh
#
# Env vars:
#   AGENT        oracle | scbe (default: oracle)
#   TASKS        comma-separated task IDs (default: hello-world)
#   OLLAMA_MODEL Ollama model for scbe agent (default: qwen2.5:7b)
#   MAX_TURNS    Max turns per task (default: 20)

set -euo pipefail

AGENT="${AGENT:-oracle}"
TASKS="${TASKS:-hello-world}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5:7b}"
MAX_TURNS="${MAX_TURNS:-20}"

REPO_WIN="C:/Users/issda/SCBE-AETHERMOORE"
REPO_WSL="/mnt/c/Users/issda/SCBE-AETHERMOORE"
DATASET_PATH="${REPO_WSL}/artifacts/benchmarks/tb-datasets/terminal-bench-core-0.1.1/tasks"
OUTPUT_PATH="${REPO_WSL}/artifacts/benchmarks/tb-runs"

export PATH="/root/.local/bin:/usr/local/bin:/usr/bin:/bin:${PATH}"
export DOCKER_HOST="unix:///run/podman/podman.sock"
export PYTHONPATH="${REPO_WSL}"

# Convert comma-separated tasks to --task-id flags
TASK_FLAGS=""
IFS=',' read -ra TASK_ARR <<< "$TASKS"
for t in "${TASK_ARR[@]}"; do
    TASK_FLAGS="$TASK_FLAGS --task-id $t"
done

if [[ "$AGENT" == "scbe" ]]; then
    echo "Running SCBE-governed agent (model: $OLLAMA_MODEL, max_turns: $MAX_TURNS)"
    tb runs create \
        --agent-module "scripts.benchmark.terminal_bench_scbe_agent:ScbeGovernedAgent" \
        --dataset-path "$DATASET_PATH" \
        --output-path "$OUTPUT_PATH" \
        --n-concurrent 1 \
        --agent-kwarg "model=${OLLAMA_MODEL}" \
        --agent-kwarg "max_turns=${MAX_TURNS}" \
        $TASK_FLAGS
else
    echo "Running agent: $AGENT"
    tb runs create \
        --agent "$AGENT" \
        --dataset-path "$DATASET_PATH" \
        --output-path "$OUTPUT_PATH" \
        --n-concurrent 1 \
        $TASK_FLAGS
fi
