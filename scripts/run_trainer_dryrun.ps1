Set-Location "C:\Users\issda\SCBE-AETHERMOORE"
Write-Host "Running HYDRA Multi-Model Trainer dry-run..." -ForegroundColor Cyan
python training/vertex_hydra_trainer.py --dry-run 2>&1 | Tee-Object -FilePath "artifacts/trainer_dryrun_output.txt"
Write-Host "`nOutput saved to artifacts/trainer_dryrun_output.txt" -ForegroundColor Green
