#!/usr/bin/env python3
"""Debug the PowerShell Ollama bridge."""
import json
import os
import subprocess

PWSH = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"

payload = {
    "model": "qwen2.5:0.5b",
    "prompt": 'Output JSON: {"commands":["echo hi"],"done":true,"rationale":"ok"}',
    "stream": False,
    "options": {"temperature": 0, "num_predict": 100},
}

win_tmp_wsl = "/mnt/c/Windows/Temp/ollama_bridge_test.json"
win_tmp_ps = "C:\\Windows\\Temp\\ollama_bridge_test.json"

with open(win_tmp_wsl, "w", encoding="utf-8") as f:
    json.dump(payload, f)

print(f"Wrote {os.path.getsize(win_tmp_wsl)} bytes to {win_tmp_wsl}")

ps_cmd = (
    f"$r = Invoke-RestMethod -Method Post "
    f"-Uri 'http://127.0.0.1:11434/api/generate' "
    f"-ContentType 'application/json' "
    f"-InFile '{win_tmp_ps}'; "
    f"Write-Output $r.response"
)

print("PS CMD:", ps_cmd[:150])

result = subprocess.run(
    [PWSH, "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
    capture_output=True, text=True, timeout=90,
)
print("RC:", result.returncode)
print("STDOUT:", repr(result.stdout[:300]))
print("STDERR:", repr(result.stderr[:400]))

os.unlink(win_tmp_wsl)
