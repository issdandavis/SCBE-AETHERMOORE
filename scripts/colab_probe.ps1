$bridge = Join-Path $PSScriptRoot '..\skills\clawhub\scbe-colab-n8n-bridge\scripts\colab_n8n_bridge.py'
python $bridge --name colab_local --probe
