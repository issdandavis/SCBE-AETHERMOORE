#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="${ROOT_DIR}/k8s/training/node-fleet-gke-automation.yaml"
NAMESPACE="scbe-training"

usage() {
  cat <<EOF
Usage:
  scripts/gke_training_oneclick.sh [--dry-run] [--suspend] [--resume] [--uninstall]

Behavior:
  default      Deploy/update namespace, secrets, and training cronjobs
  --suspend    Suspend both cronjobs
  --resume     Resume both cronjobs
  --uninstall  Remove automation manifest
  --dry-run    Print kubectl commands without executing

Required env for deploy path:
  HF_TOKEN
  NOTION_TOKEN
EOF
}

run_cmd() {
  if [[ "${DRY_RUN}" == "true" ]]; then
    printf '[dry-run] %s\n' "$*"
  else
    eval "$@"
  fi
}

patch_suspend() {
  local value="$1"
  run_cmd "kubectl -n ${NAMESPACE} patch cronjob codex-ingest-daily -p '{\"spec\":{\"suspend\":${value}}}'"
  run_cmd "kubectl -n ${NAMESPACE} patch cronjob node-fleet-train-6h -p '{\"spec\":{\"suspend\":${value}}}'"
}

DRY_RUN="false"
MODE="deploy"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN="true" ;;
    --suspend) MODE="suspend" ;;
    --resume) MODE="resume" ;;
    --uninstall) MODE="uninstall" ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1"; usage; exit 1 ;;
  esac
  shift
done

if [[ ! -f "${MANIFEST}" ]]; then
  echo "Manifest missing: ${MANIFEST}" >&2
  exit 1
fi

if [[ "${MODE}" == "suspend" ]]; then
  patch_suspend "true"
  exit 0
fi

if [[ "${MODE}" == "resume" ]]; then
  patch_suspend "false"
  exit 0
fi

if [[ "${MODE}" == "uninstall" ]]; then
  run_cmd "kubectl delete -f '${MANIFEST}'"
  exit 0
fi

if [[ -z "${HF_TOKEN:-}" || -z "${NOTION_TOKEN:-}" ]]; then
  echo "HF_TOKEN and NOTION_TOKEN must be set for deploy mode." >&2
  exit 1
fi

run_cmd "kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -"
run_cmd "kubectl -n ${NAMESPACE} create secret generic hf-secrets --from-literal=token='${HF_TOKEN}' --dry-run=client -o yaml | kubectl apply -f -"
run_cmd "kubectl -n ${NAMESPACE} create secret generic notion-secrets --from-literal=token='${NOTION_TOKEN}' --dry-run=client -o yaml | kubectl apply -f -"
run_cmd "kubectl apply -f '${MANIFEST}'"
run_cmd "kubectl -n ${NAMESPACE} get cronjobs"

echo "GKE training automation deploy complete."

