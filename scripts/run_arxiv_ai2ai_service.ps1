param(
  [string]$Host = "127.0.0.1",
  [int]$Port = 8099
)

Set-Location "C:/Users/issda/SCBE-AETHERMOORE"
python -m uvicorn scripts.arxiv_ai2ai_service:app --host $Host --port $Port
