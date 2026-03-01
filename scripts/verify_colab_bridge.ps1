$bridge = 'C:\Users\issda\SCBE-AETHERMOORE\skills\clawhub\scbe-colab-n8n-bridge\scripts\colab_n8n_bridge.py'
$profile = 'colab_local'

Write-Host "[1] status"
python $bridge --name $profile --status --format json

Write-Host "[2] probe"
python $bridge --name $profile --probe

Write-Host "[3] env"
python $bridge --name $profile --env --shell pwsh
