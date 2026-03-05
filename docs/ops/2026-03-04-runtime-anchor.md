# Runtime Anchor Status - 2026-03-04

Owner: Worker A (`Runtime-Anchor`)  
Lane: runtime reliability only

## Commands Run

1. Dual-side smoke on current gateway (`8500`)
   - `python scripts/system/smoke_aethercode_gateway.py --base-url http://127.0.0.1:8500 --timeout-sec 5 --output artifacts/system_smoke/runtime_anchor_baseline_127.json --print-json`
   - `python scripts/system/smoke_aethercode_gateway.py --base-url http://localhost:8500 --timeout-sec 5 --output artifacts/system_smoke/runtime_anchor_baseline_localhost.json --print-json`
   - Result: PASS (`7/7` checks each, `required_failures=0`)

2. Launcher mode validation: `-CheckOnly`
   - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_aethercode.ps1 -Port 8500 -CheckOnly`
   - Result: PASS (`EXIT_CODE=0`, smoke `7/7`)
   - Evidence: `artifacts/system_smoke/runtime_anchor_mode_checkonly.log`

3. Launcher mode validation: `-Smoke`
   - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_aethercode.ps1 -Port 8500 -Smoke`
   - Result: PASS (`EXIT_CODE=0`, smoke `7/7`)
   - Evidence: `artifacts/system_smoke/runtime_anchor_mode_smoke.log`

4. Launcher mode validation: `-Detached`
   - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_aethercode.ps1 -Port 8510 -Detached -Smoke -StartupTimeoutSec 20`
   - Result: PASS (`EXIT_CODE=0`, spawned PID observed listening, terminated cleanly)
   - Evidence: `artifacts/system_smoke/runtime_anchor_mode_detached.log`

5. Launcher mode validation: `-AutoPort` (forced busy/unhealthy branch)
   - Occupied test port with local TCP listener job, then:
   - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_aethercode.ps1 -Port 8530 -AutoPort -Detached -Smoke -StartupTimeoutSec 20`
   - Result: PASS (`EXIT_CODE=0`, selected free port `8531`, smoke `7/7`, detached PID terminated)
   - Evidence: `artifacts/system_smoke/runtime_anchor_mode_autoport_forced_busy.log`

6. Interaction check: `-Detached -AutoPort` on live healthy `8500`
   - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_aethercode.ps1 -Port 8500 -Detached -AutoPort -Smoke`
   - Result: PASS (`EXIT_CODE=0`), reused existing healthy gateway at `8500`
   - Evidence: `artifacts/system_smoke/runtime_anchor_mode_detached_autoport_on_live8500.log`

## Pass/Fail Summary

- `-CheckOnly`: PASS
- `-Smoke`: PASS
- `-Detached`: PASS
- `-AutoPort`: PASS (validated on busy/unhealthy occupied port)
- Dual-side gateway smoke (`127.0.0.1`, `localhost`): PASS

## Risks / Notes

1. `-AutoPort` is only applied when the requested port is occupied **and unhealthy**. If the occupied port is already healthy (example: `8500`), launcher exits against the existing service and does not relocate.
2. `scripts/system/smoke_aethercode_gateway.py` default output (`artifacts/system_smoke/aethercode_gateway_smoke.json`) is overwritten on each run unless `--output` is provided.
3. `localhost` probes were consistently slower than `127.0.0.1` during this run (still passing).

## Blockers

None.
