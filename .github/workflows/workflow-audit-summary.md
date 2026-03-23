# Workflow Governance Audit

- Total workflows: 60
- Total findings: 57
- High: 31
- Medium: 22
- Low: 4

## auto-publish.yml

- [HIGH] line 86: MASKED_ERROR_OR_ECHO (Error masking can hide failures and create false-positive success.)
  - `PREV_TAG=$(git describe --tags --abbrev=0 HEAD^ 2>/dev/null || echo "")`

## auto-resolve-conflicts.yml

- [HIGH] line 40: MASKED_ERROR_OR_TRUE (Error masking can hide failing CI checks.)
  - `git merge origin/main --no-commit --no-ff 2>/dev/null || true`
- [HIGH] line 45: MASKED_ERROR_OR_TRUE (Error masking can hide failing CI checks.)
  - `git merge --abort 2>/dev/null || true`

## ci.yml

- [MEDIUM] line 102: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 157: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 161: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`

## coherence-gate.yml

- [MEDIUM] line 54: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`

## daily-review.yml

- [HIGH] line 52: MASKED_ERROR_OR_TRUE (Error masking can hide failing CI checks.)
  - `pytest tests/ -v --ignore=tests/node_modules 2>&1 || true`
- [MEDIUM] line 31: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 35: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 44: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 49: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 59: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 64: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 70: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`

## daily_ops.yml

- [LOW] line 39: SET_PLUS_E_WITHOUT_EXIT_HANDLING (set +e requires explicit status handling to avoid silent failures.)
  - `set +e`
- [LOW] line 215: SET_PLUS_E_WITHOUT_EXIT_HANDLING (set +e requires explicit status handling to avoid silent failures.)
  - `set +e`

## deploy-aws.yml

- [HIGH] line 175: MASKED_ERROR_OR_TRUE (Error masking can hide failing CI checks.)
  - `2>/dev/null || true`
- [HIGH] line 180: MASKED_ERROR_OR_TRUE (Error masking can hide failing CI checks.)
  - `2>/dev/null || true`
- [HIGH] line 266: MASKED_ERROR_OR_TRUE (Error masking can hide failing CI checks.)
  - `2>/dev/null || true`
- [HIGH] line 129: MASKED_ERROR_OR_ECHO (Error masking can hide failures and create false-positive success.)
  - `--query 'FunctionUrl' --output text 2>/dev/null || echo "")`
- [HIGH] line 276: MASKED_ERROR_OR_ECHO (Error masking can hide failures and create false-positive success.)
  - `curl -s "${API_URL}/v1/health" | jq . || echo "Health check pending..."`

## deploy-eks.yml

- [HIGH] line 51: MASKED_ERROR_OR_ECHO (Error masking can hide failures and create false-positive success.)
  - `kubectl apply -f k8s/agent-manifests/ || echo "Agent manifests applied with warnings"`
- [HIGH] line 70: MASKED_ERROR_OR_ECHO (Error masking can hide failures and create false-positive success.)
  - `SVC_URL=$(kubectl get svc scbe-aethermoore-service -n scbe-aethermoore -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")`
- [HIGH] line 73: MASKED_ERROR_OR_ECHO (Error masking can hide failures and create false-positive success.)
  - `curl -s --max-time 10 "http://$SVC_URL/" || echo "Service not yet reachable (LoadBalancer may need time)"`

## deploy-gke.yml

- [HIGH] line 118: MASKED_ERROR_OR_ECHO (Error masking can hide failures and create false-positive success.)
  - `|| echo " - Health check pending (service starting)"`

## huggingface-sync.yml

- [HIGH] line 41: MASKED_ERROR_OR_ECHO (Error masking can hide failures and create false-positive success.)
  - `--token $HF_TOKEN || echo "Primary sync failed, continuing..."`
- [HIGH] line 52: MASKED_ERROR_OR_ECHO (Error masking can hide failures and create false-positive success.)
  - `--token $HF_TOKEN || echo "Backup sync failed, continuing..."`
- [HIGH] line 70: MASKED_ERROR_OR_ECHO (Error masking can hide failures and create false-positive success.)
  - `curl -sf https://huggingface.co/api/models/$PRIMARY_HF_REPO > /dev/null && echo "Primary: OK" || echo "Primary: UNREACHABLE"`
- [HIGH] line 72: MASKED_ERROR_OR_ECHO (Error masking can hide failures and create false-positive success.)
  - `curl -sf https://huggingface.co/api/models/$BACKUP_HF_REPO > /dev/null && echo "Backup: OK" || echo "Backup: UNREACHABLE"`

## interface-pr-ops-runner.yml

- [HIGH] line 54: MASKED_ERROR_OR_TRUE (Error masking can hide failing CI checks.)
  - `wc -l pr_queue.jsonl || true`

## kindle-build.yml

- [HIGH] line 163: MASKED_ERROR_OR_TRUE (Error masking can hide failing CI checks.)
  - `ls kindle-app/android/app/build/outputs/bundle/release/*.aab 2>/dev/null && echo "- Release AAB: uploaded (Play Store ready)" >> $GITHUB_STEP_SUMMARY || true`
- [HIGH] line 164: MASKED_ERROR_OR_TRUE (Error masking can hide failing CI checks.)
  - `ls kindle-app/android/app/build/outputs/apk/release/*.apk 2>/dev/null && echo "- Release APK: uploaded (Amazon ready)" >> $GITHUB_STEP_SUMMARY || true`

## notion-to-dataset.yml

- [MEDIUM] line 93: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`

## npm-publish.yml

- [HIGH] line 71: MASKED_ERROR_OR_TRUE (Error masking can hide failing CI checks.)
  - `last_tag=$(git describe --tags --abbrev=0 2>/dev/null || true)`

## overnight-pipeline.yml

- [HIGH] line 43: MASKED_ERROR_OR_TRUE (Error masking can hide failing CI checks.)
  - `pip install -r requirements.txt 2>/dev/null || pip install pytest hypothesis numpy 2>/dev/null || true`
- [HIGH] line 44: MASKED_ERROR_OR_TRUE (Error masking can hide failing CI checks.)
  - `npm ci 2>/dev/null || true`
- [HIGH] line 89: MASKED_ERROR_OR_TRUE (Error masking can hide failing CI checks.)
  - `run: pip install -r requirements.txt 2>/dev/null || pip install pytest hypothesis numpy scipy 2>/dev/null || true`
- [HIGH] line 139: MASKED_ERROR_OR_TRUE (Error masking can hide failing CI checks.)
  - `run: pip install -r requirements.txt 2>/dev/null || pip install pytest hypothesis numpy scipy huggingface_hub 2>/dev/null || true`
- [HIGH] line 194: MASKED_ERROR_OR_TRUE (Error masking can hide failing CI checks.)
  - `pip install -r requirements.txt 2>/dev/null || true`
- [HIGH] line 195: MASKED_ERROR_OR_TRUE (Error masking can hide failing CI checks.)
  - `npm ci 2>/dev/null || true`
- [HIGH] line 261: MASKED_ERROR_OR_TRUE (Error masking can hide failing CI checks.)
  - `run: pip install huggingface_hub datasets pytest numpy 2>/dev/null || true`
- [HIGH] line 348: MASKED_ERROR_OR_TRUE (Error masking can hide failing CI checks.)
  - `run: pip install huggingface_hub google-genai requests 2>/dev/null || true`
- [MEDIUM] line 96: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 146: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 201: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 355: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`

## pqc-python.yml

- [HIGH] line 43: MASKED_ERROR_OR_TRUE (Error masking can hide failing CI checks.)
  - `ldconfig -p | grep oqs || true`

## release.yml

- [HIGH] line 40: MASKED_ERROR_OR_ECHO (Error masking can hide failures and create false-positive success.)
  - `ls -la packages/ 2>/dev/null || echo "No packages/ directory"`
- [MEDIUM] line 52: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`

## security-checks.yml

- [MEDIUM] line 48: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 56: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 62: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`

## weekly-security-audit.yml

- [MEDIUM] line 121: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 128: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [LOW] line 28: SET_PLUS_E_WITHOUT_EXIT_HANDLING (set +e requires explicit status handling to avoid silent failures.)
  - `set +e`
- [LOW] line 94: SET_PLUS_E_WITHOUT_EXIT_HANDLING (set +e requires explicit status handling to avoid silent failures.)
  - `set +e`

