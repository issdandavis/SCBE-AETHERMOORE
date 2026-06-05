#!/usr/bin/env python3
"""Debug ask_ollama: trace the flow step by step."""
import json
import os
import subprocess
import urllib.request

PWSH = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
HOST = "http://127.0.0.1:11434"
MODEL = "qwen2.5:0.5b"

payload_dict = {
    "model": MODEL,
    "prompt": 'Output JSON: {"commands":["echo hi"],"done":true,"rationale":"ok"}',
    "stream": False,
    "options": {"temperature": 0, "num_predict": 100},
}
payload = json.dumps(payload_dict).encode()

# Step 1: try direct HTTP
print("Step 1: direct HTTP")
try:
    req = urllib.request.Request(
        f"{HOST}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read())
        print("  Direct HTTP OK, response:", repr(data.get("response", "")[:100]))
except Exception as e:
    print(f"  Direct HTTP failed: {type(e).__name__}: {e}")

# Step 2: PowerShell bridge
print("Step 2: PowerShell bridge")
pid = os.getpid()
win_tmp_wsl = f"/mnt/c/Windows/Temp/ollama_bridge_{pid}.json"
win_tmp_ps = f"C:\\Windows\\Temp\\ollama_bridge_{pid}.json"
with open(win_tmp_wsl, "wb") as f:
    f.write(payload)

ps_cmd = (
    f"$r = Invoke-RestMethod -Method Post "
    f"-Uri 'http://127.0.0.1:11434/api/generate' "
    f"-ContentType 'application/json' "
    f"-InFile '{win_tmp_ps}'; "
    f"Write-Output $r.response"
)
result = subprocess.run(
    [PWSH, "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
    capture_output=True, text=True, timeout=90,
)
os.unlink(win_tmp_wsl)
print(f"  RC: {result.returncode}")
print(f"  STDOUT: {repr(result.stdout[:200])}")
print(f"  STDERR: {repr(result.stderr[:200])}")
