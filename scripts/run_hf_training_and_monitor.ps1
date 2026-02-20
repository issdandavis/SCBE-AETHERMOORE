param(
    [string]$DatasetRepo = "issdandavis/scbe-aethermoore-training-data",
    [string]$ModelRepo = "issdandavis/phdm-21d-embedding",
    [int]$Epochs = 10,
    [int]$EmbeddingDim = 256,
    [double]$LearningRate = 0.18
)

$ErrorActionPreference = "Stop"

$runId = Get-Date -Format "yyyyMMddTHHmmssZ"
$runDir = "training/runs/huggingface/$runId"

python scripts/train_hf_longrun_placeholder.py `
  --dataset-repo $DatasetRepo `
  --model-repo $ModelRepo `
  --run-dir $runDir `
  --epochs $Epochs `
  --embedding-dim $EmbeddingDim `
  --learning-rate $LearningRate

if ($LASTEXITCODE -ne 0) {
  throw "Training failed."
}

python scripts/monitor_training_growth.py --run-dir $runDir
if ($LASTEXITCODE -ne 0) {
  throw "Growth monitor failed."
}

Write-Host ""
Write-Host "DONE" -ForegroundColor Green
Write-Host "Run directory: $runDir"

