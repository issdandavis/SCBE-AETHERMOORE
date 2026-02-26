param(
    [switch]$SkipAuth
)

Write-Host "`n===== HYDRA Vertex AI Setup =====" -ForegroundColor Cyan
Write-Host ""

$PROJECT_ID = "gen-lang-client-0103521392"
$REGION = "us-central1"

# Step 1: Check gcloud
Write-Host "--- Step 1: Check gcloud CLI ---"
$gcVersion = gcloud version --format="value(Google Cloud SDK)" 2>$null
if ($gcVersion) {
    Write-Host "  gcloud SDK: $gcVersion" -ForegroundColor Green
} else {
    Write-Host "  gcloud not found!" -ForegroundColor Red
    Write-Host "  Install from: https://cloud.google.com/sdk/docs/install" -ForegroundColor Yellow
    Write-Host "  Or run: winget install Google.CloudSDK" -ForegroundColor Yellow
    exit 1
}

# Step 2: Authenticate
Write-Host ""
Write-Host "--- Step 2: Authentication ---"
if (-not $SkipAuth) {
    Write-Host "  Opening browser for auth..." -ForegroundColor Yellow
    gcloud auth login
    gcloud auth application-default login
} else {
    Write-Host "  [skip] Auth skipped (-SkipAuth)" -ForegroundColor DarkGray
}

# Step 3: Set project
Write-Host ""
Write-Host "--- Step 3: Set project ---"
gcloud config set project $PROJECT_ID
Write-Host "  Project: $PROJECT_ID" -ForegroundColor Green

# Step 4: Enable APIs
Write-Host ""
Write-Host "--- Step 4: Enable required APIs ---"
$apis = @(
    "aiplatform.googleapis.com",          # Vertex AI
    "artifactregistry.googleapis.com",    # Docker images
    "cloudbuild.googleapis.com",          # Cloud Build
    "storage.googleapis.com",             # Cloud Storage
    "compute.googleapis.com",             # Compute Engine
    "container.googleapis.com"            # GKE
)

foreach ($api in $apis) {
    Write-Host "  Enabling $api..."
    gcloud services enable $api 2>$null
}
Write-Host "  All APIs enabled." -ForegroundColor Green

# Step 5: Check Vertex AI quota
Write-Host ""
Write-Host "--- Step 5: Check GPU quota ---"
Write-Host "  Region: $REGION" -ForegroundColor Cyan
Write-Host "  Checking T4 GPU availability..."
$quotas = gcloud compute regions describe $REGION --format="json" 2>$null | ConvertFrom-Json
if ($quotas) {
    $gpuQuota = $quotas.quotas | Where-Object { $_.metric -like "*GPU*" }
    foreach ($q in $gpuQuota) {
        Write-Host "  $($q.metric): $($q.usage)/$($q.limit)" -ForegroundColor $(if ($q.usage -lt $q.limit) { "Green" } else { "Red" })
    }
} else {
    Write-Host "  Could not fetch quota info (check auth)" -ForegroundColor Yellow
}

# Step 6: Create Cloud Storage bucket for training artifacts
Write-Host ""
Write-Host "--- Step 6: Training artifact bucket ---"
$BUCKET = "gs://scbe-hydra-training"
$exists = gsutil ls $BUCKET 2>$null
if ($exists) {
    Write-Host "  Bucket exists: $BUCKET" -ForegroundColor Green
} else {
    Write-Host "  Creating bucket: $BUCKET"
    gsutil mb -l $REGION -p $PROJECT_ID $BUCKET
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Created: $BUCKET" -ForegroundColor Green
    } else {
        Write-Host "  Bucket creation failed (may need unique name)" -ForegroundColor Yellow
    }
}

# Step 7: Verify Python + deps
Write-Host ""
Write-Host "--- Step 7: Python dependencies ---"
$pyVersion = python --version 2>&1
Write-Host "  Python: $pyVersion"

Write-Host "  Checking training dependencies..."
$deps = @("yaml", "torch", "transformers", "peft", "trl", "datasets", "huggingface_hub")
foreach ($dep in $deps) {
    $check = python -c "import $dep; print($dep.__version__ if hasattr($dep, '__version__') else 'ok')" 2>$null
    if ($check) {
        Write-Host "    $dep = $check" -ForegroundColor Green
    } else {
        Write-Host "    $dep = NOT INSTALLED" -ForegroundColor Yellow
    }
}

# Step 8: Dry run the trainer
Write-Host ""
Write-Host "--- Step 8: Trainer dry run ---"
$trainerPath = Join-Path $PSScriptRoot "..\training\vertex_hydra_trainer.py"
if (Test-Path $trainerPath) {
    python $trainerPath --dry-run
} else {
    Write-Host "  Trainer not found at $trainerPath" -ForegroundColor Red
}

Write-Host ""
Write-Host "===== Setup Complete =====" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. Train KO head (fastest):     python training/vertex_hydra_trainer.py --head KO" -ForegroundColor White
Write-Host "  2. Train all heads:              python training/vertex_hydra_trainer.py --all" -ForegroundColor White
Write-Host "  3. Train on Vertex AI:           python training/vertex_hydra_trainer.py --head RU --vertex" -ForegroundColor White
Write-Host "  4. Push to HuggingFace:          python training/vertex_hydra_trainer.py --all --push" -ForegroundColor White
Write-Host "  5. Use Colab notebook:           notebooks/scbe_cloud_workspace.ipynb" -ForegroundColor White
Write-Host ""
