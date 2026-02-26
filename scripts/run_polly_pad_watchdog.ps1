param(
  [string]$SwitchboardDb = "artifacts/hydra/headless_ide/switchboard.db",
  [string]$PadDb = "artifacts/hydra/polly_pad/pads.db",
  [int]$ScanLimit = 50
)

$ErrorActionPreference = "Stop"

python scripts/polly_pad_watchdog.py `
  --switchboard-db $SwitchboardDb `
  --pad-db $PadDb `
  --scan-limit $ScanLimit
