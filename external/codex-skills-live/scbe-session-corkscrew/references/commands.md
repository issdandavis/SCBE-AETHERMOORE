# Session Corkscrew Commands

## Start fresh session
```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/terminal_crosstalk_emit.ps1 -NewSession -TaskId "SESSION-START" -Summary "Session kickoff"
```

## Emit packet in current session
```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/terminal_crosstalk_emit.ps1 -TaskId "TASK-ID" -Summary "Progress" -NextAction "handoff"
```

## Sign on with callsign
```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/session_signon.ps1 -Agent "Codex" -Callsign "Helix Warden" -Status active -Summary "Session start"
```

## Verify session
```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/session_signon.ps1 -Agent "Codex" -Callsign "Helix Warden" -SessionId "<session-id>" -Status verified -Summary "Validated"
```

## Retire session
```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/session_signon.ps1 -Agent "Codex" -Callsign "Helix Warden" -SessionId "<session-id>" -Status retired -Summary "Closed"
```

## Quick checks
```powershell
Get-Content artifacts/agent_comm/github_lanes/cross_talk.jsonl -Tail 5
Get-Content notes/session_signons.md -Head 30
Get-Content artifacts/agent_comm/session_signons.jsonl -Tail 10
```
