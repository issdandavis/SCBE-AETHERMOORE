param(
    [switch]$DryRun
)

Set-Location "C:\Users\issda\SCBE-AETHERMOORE"
$outFile = "artifacts/git_push_output.txt"
New-Item -ItemType Directory -Path "artifacts" -Force | Out-Null

$log = @()
function Log($msg) {
    Write-Host $msg
    $script:log += $msg
}

Log "===== SCBE Git Push ====="
Log ""

# Step 1: Status
Log "--- Step 1: Git Status ---"
$status = git status --porcelain 2>&1
$status | ForEach-Object { Log "  $_" }
Log ""

# Step 2: Current branch
$branch = git branch --show-current 2>&1
Log "Branch: $branch"
Log ""

# Step 3: Recent commits for style reference
Log "--- Recent commits ---"
$commits = git log --oneline -5 2>&1
$commits | ForEach-Object { Log "  $_" }
Log ""

# Step 4: Diff stats
Log "--- Diff Stats ---"
$diffStat = git diff --stat 2>&1
$diffStat | ForEach-Object { Log "  $_" }
Log ""

# Step 5: Add all new and modified files
Log "--- Step 5: Stage files ---"
$filesToAdd = @(
    'src/browser/hydra_hand.py'
    'training/hydra_multi_model_config.yaml'
    'training/vertex_hydra_trainer.py'
    'training/vertex_pipeline_config.yaml'
    'training-data/theory_doc_architecture_theory.jsonl'
    'training-data/theory_doc_patent_claims.jsonl'
    'training-data/theory_doc_security_attacks.jsonl'
    'training-data/theory_doc_geoseal_crypto.jsonl'
    'training-data/theory_doc_conlang_intent.jsonl'
    'training-data/theory_doc_spiralverse_lore.jsonl'
    'notebooks/scbe_cloud_workspace.ipynb'
    'scripts/setup_playwright.ps1'
    'scripts/headless_browser.py'
    'scripts/setup_gcloud_vertex.ps1'
    'scripts/run_trainer_dryrun.ps1'
    'scripts/system/quick_disk_check.ps1'
    'scripts/system/deep_cleanup.ps1'
    'scripts/deploy_gke.sh'
    'api/main.py'
    'src/api/main.py'
    'src/api/mesh_routes.py'
    'src/mcp_server/semantic_mesh.py'
    'src/mcp_server/selftest.py'
    'src/mcp_server/__init__.py'
    'k8s/deployment.yaml'
    'k8s/service.yaml'
    'k8s/agent-manifests/private-agents.yaml'
    'k8s/agent-manifests/public-gateway.yaml'
    'k8s/agent-manifests/kafka.yaml'
    'k8s/agent-manifests/kustomization.yaml'
    '.github/workflows/deploy-gke.yml'
    '.github/workflows/vertex-training.yml'
    'Dockerfile.api'
    'demo/npc_gateway.py'
    'src/symphonic_cipher/scbe_aethermoore/gate_swap.py'
    'tests/test_gate_swap_trimanifold.py'
    'scripts/git_push_all.ps1'
)

foreach ($f in $filesToAdd) {
    if (Test-Path $f) {
        if ($DryRun) {
            Log "  [would add] $f"
        } else {
            git add $f 2>&1 | Out-Null
            Log "  [added] $f"
        }
    } else {
        Log "  [skip] $f (not found)"
    }
}

# Also add any new files in the scripts directory
git add scripts/*.ps1 scripts/*.py 2>&1 | Out-Null
git add scripts/system/*.ps1 2>&1 | Out-Null
Log ""

# Step 6: Show what's staged
Log "--- Staged changes ---"
$staged = git diff --cached --stat 2>&1
$staged | ForEach-Object { Log "  $_" }
Log ""

# Step 7: Commit
if (-not $DryRun) {
    Log "--- Step 7: Commit ---"

    # Write commit message to temp file (avoids all PowerShell string parsing)
    $commitFile = 'artifacts/commit_msg.txt'
    Set-Content -Path $commitFile -Value @'
feat(hydra): multi-model training pipeline + HYDRA Hand browser squad

* HYDRA Hand (969 lines): 6 Sacred Tongue browser fingers with
  multi-action dispatch, swarm research, HydraSpine integration,
  SemanticMesh ingest, proximity-based throttling

* Multi-model trainer: 6 open-source base models (TinyLlama, Moondream2,
  Phi-2, Qwen2.5-1.5B, SmolLM-1.7B) mapped to HYDRA heads with QLoRA
  4-bit fine-tuning, TriManifoldLattice governance gate, Vertex AI
  submission support. 17,906 training pairs across all heads.

* 97 new SFT pairs from 500-page theory document (architecture, patents,
  security, GeoSeal crypto, conlang intent, Spiralverse lore)

* GKE deployment fixes: correct project ID, GCR images, GKE NEG
  annotations, standard-rwo storage class

* Semantic mesh routes wired into both API apps
* Vertex AI config: fixed project ID and cluster references
* Colab notebook: added multi-model HYDRA training cells
* Playwright setup scripts + headless browser CLI
* Disk management scripts (audit + cleanup)

* Gate swap module: int->NegaBinary->BalancedTernary->MSD pipeline
  with TriManifold governance (ALLOW/QUARANTINE/DENY), 44 tests
  covering all 27 trit combinations exhaustively

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
'@
    git commit -F $commitFile 2>&1 | ForEach-Object { Log "  $_" }
    Remove-Item $commitFile -ErrorAction SilentlyContinue
    Log ""

    # Step 8: Push
    Log "--- Step 8: Push ---"
    $pushResult = git push origin $branch 2>&1
    $pushResult | ForEach-Object { Log "  $_" }
    Log ""

    # Step 9: Verify with gh
    Log "--- Step 9: Verify ---"
    $ghStatus = gh repo view --json name,defaultBranchRef 2>&1
    Log "  Repo: $ghStatus"

    # Check if there's an open PR for this branch
    $prList = gh pr list --head $branch --json number,title,state 2>&1
    Log "  PRs for ${branch}: $prList"

    # If no PR exists, create one
    if ($prList -eq '[]' -or $prList -match 'no pull requests') {
        Log ""
        Log "--- Creating PR ---"
        $prBodyFile = 'artifacts/pr_body.txt'
        Set-Content -Path $prBodyFile -Value @'
## Summary
* HYDRA Hand multi-headed browser squad (969 lines, 5 features)
* Multi-model training pipeline for 6 Sacred Tongue heads
* 97 new SFT pairs from theory document extraction
* GKE deployment fixes (project ID, annotations, storage)
* Semantic mesh API routes + Vertex AI config fixes
* Colab notebook with multi-model training cells
* Playwright setup + headless browser CLI
* Disk management scripts
* Gate swap module: NegaBinary->BalancedTernary->MSD pipeline (44 tests, 137 total green)

## Test plan
* [ ] `python training/vertex_hydra_trainer.py --dry-run` passes all 6 heads
* [ ] Colab notebook runs setup + training cells
* [ ] HYDRA Hand import works: `python -c "from src.browser.hydra_hand import HydraHand"`
* [ ] API starts: `python -m uvicorn src.api.main:app`

Generated with [Claude Code](https://claude.com/claude-code)
'@
        $prResult = gh pr create --title 'feat(hydra): multi-model training + browser squad' --body-file $prBodyFile 2>&1
        $prResult | ForEach-Object { Log "  $_" }
        Remove-Item $prBodyFile -ErrorAction SilentlyContinue
    }
} else {
    Log "--- DRY RUN --- no commit or push ---"
}

Log ""
Log "===== Done ====="

# Save output
$log | Out-File -FilePath $outFile -Encoding utf8
Log "Output saved to $outFile"
