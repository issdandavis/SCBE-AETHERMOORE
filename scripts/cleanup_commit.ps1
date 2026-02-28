Set-Location "C:\Users\issda\SCBE-AETHERMOORE"

Write-Host "=== Step 1: Remove .hypothesis from git tracking ===" -ForegroundColor Cyan
git rm -r --cached .hypothesis/ 2>&1
Write-Host ""

Write-Host "=== Step 2: Add artifacts/ to .gitignore ===" -ForegroundColor Cyan
# Add full artifacts/ ignore if not already there
$gitignore = Get-Content .gitignore -Raw
if ($gitignore -notmatch '(?m)^artifacts/$') {
    Add-Content .gitignore "`nartifacts/"
    Write-Host "  Added 'artifacts/' to .gitignore"
} else {
    Write-Host "  'artifacts/' already in .gitignore"
}
Write-Host ""

Write-Host "=== Step 3: Stage all modified files ===" -ForegroundColor Cyan
$modified = @(
    '.claude/settings.local.json'
    '.github/workflows/deploy-gke.yml'
    '.github/workflows/vertex-training.yml'
    'Dockerfile.api'
    'api/main.py'
    'demo/aethermoor_game.py'
    'demo/dungeon.py'
    'demo/engine.py'
    'demo/tilemap.py'
    'k8s/agent-manifests/kafka.yaml'
    'k8s/agent-manifests/kustomization.yaml'
    'k8s/agent-manifests/private-agents.yaml'
    'k8s/agent-manifests/public-gateway.yaml'
    'k8s/deployment.yaml'
    'k8s/service.yaml'
    'src/api/main.py'
    'src/crypto/__init__.py'
    'src/gacha_isekai/__init__.py'
    'training/ingest/latest_local_cloud_sync.txt'
    'training/ingest/local_cloud_sync_state.json'
    'training/vertex_pipeline_config.yaml'
    'workflows/n8n/scbe_n8n_bridge.py'
    '.gitignore'
)
foreach ($f in $modified) {
    if (Test-Path $f) {
        git add $f 2>&1 | Out-Null
        Write-Host "  [staged] $f"
    }
}
Write-Host ""

Write-Host "=== Step 4: Stage new files ===" -ForegroundColor Cyan
$newFiles = @(
    'demo/aether_eggs.py'
    'demo/atla.py'
    'demo/georama.py'
    'demo/npc_gateway.py'
    'demo/save_system.py'
    'demo/weapons.py'
    'notebooks/colab_aethermoor_finetune.ipynb'
    'notebooks/scbe_cloud_workspace.ipynb'
    'scripts/convert_to_chat_format.py'
    'scripts/deploy_gke.sh'
    'scripts/git_push_all.ps1'
    'scripts/cleanup_commit.ps1'
    'scripts/headless_browser.py'
    'scripts/run_trainer_dryrun.ps1'
    'scripts/setup_gcloud_vertex.ps1'
    'scripts/setup_playwright.ps1'
    'scripts/system/deep_cleanup.ps1'
    'scripts/system/quick_disk_check.ps1'
    'src/api/mesh_routes.py'
    'src/browser/hydra_hand.py'
    'src/crypto/quasicrystal_lattice.py'
    'src/gacha_isekai/personality_cluster_lattice.py'
    'src/gacha_isekai/personality_manifold.py'
    'src/gacha_isekai/personality_tri_manifold.py'
    'src/mcp_server/__init__.py'
    'src/mcp_server/selftest.py'
    'src/mcp_server/semantic_mesh.py'
    'src/symphonic_cipher/scbe_aethermoore/gate_swap.py'
    'tests/test_gate_swap_trimanifold.py'
    'training-data/game_sessions/session_test_session.jsonl'
    'training-data/theory_doc_architecture_theory.jsonl'
    'training-data/theory_doc_conlang_intent.jsonl'
    'training-data/theory_doc_geoseal_crypto.jsonl'
    'training-data/theory_doc_patent_claims.jsonl'
    'training-data/theory_doc_security_attacks.jsonl'
    'training-data/theory_doc_spiralverse_lore.jsonl'
    'training/hydra_multi_model_config.yaml'
    'training/vertex_hydra_trainer.py'
    'workflows/n8n/vertex_hf_pipeline.workflow.json'
)
foreach ($f in $newFiles) {
    if (Test-Path $f) {
        git add $f 2>&1 | Out-Null
        Write-Host "  [staged] $f"
    }
}
Write-Host ""

Write-Host "=== Step 5: Skip binary/temp files ===" -ForegroundColor Cyan
Write-Host "  Skipping: GIFs, PNGs, saves/, tuxemon_src/, audio/, tmp_*.xml"
Write-Host "  (These belong in .gitignore or LFS, not in git)"
# Add them to gitignore
$skipPatterns = @(
    '*.gif'
    'demo/saves/'
    'demo/tuxemon_src/'
    'demo/*.png'
    'training-data/audio/'
    'tmp_*.xml'
)
foreach ($p in $skipPatterns) {
    if ($gitignore -notmatch [regex]::Escape($p)) {
        Add-Content .gitignore $p
        Write-Host "  Added '$p' to .gitignore"
    }
}
git add .gitignore 2>&1 | Out-Null
Write-Host ""

Write-Host "=== Step 6: Show staged summary ===" -ForegroundColor Cyan
git diff --cached --stat
Write-Host ""

Write-Host "=== Step 7: Commit ===" -ForegroundColor Cyan
$commitFile = 'artifacts/commit_msg.txt'
Set-Content -Path $commitFile -Value @'
chore: clean up working tree after PR #290 merge

* Remove .hypothesis/ from git tracking (already in .gitignore)
* Stage all modified configs, k8s manifests, demo games, API files
* Stage new files: gate_swap, personality manifolds, quasicrystal lattice
* Add artifacts/, GIFs, PNGs, temp files to .gitignore
* 1192 hypothesis cache deletions resolved

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
'@
git commit -F $commitFile 2>&1
Remove-Item $commitFile -ErrorAction SilentlyContinue
Write-Host ""

Write-Host "=== Step 8: Push ===" -ForegroundColor Cyan
$branch = git branch --show-current
git push origin $branch 2>&1
Write-Host ""

Write-Host "=== Step 9: Verify clean ===" -ForegroundColor Cyan
git status --short
Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Green
