# Install Gate for `scbe-kernel-external-toolcall-specialist`

This skill is install-gated. Do not install without explicit human approval.

## Target install path

- `C:\Users\issda\.codex\skills\scbe-kernel-external-toolcall-specialist`

## Required approval phrase

One of:

- `approved`
- `yes`
- `install approved`

## Install command (PowerShell)

```powershell
$src = "C:\Users\issda\SCBE-AETHERMOORE\skills\scbe-kernel-external-toolcall-specialist"
$dst = "C:\Users\issda\.codex\skills\scbe-kernel-external-toolcall-specialist"
Copy-Item -Path $src -Destination $dst -Recurse -Force
```

## Hash capture for audit

```powershell
Get-ChildItem -Path "C:\Users\issda\SCBE-AETHERMOORE\skills\scbe-kernel-external-toolcall-specialist" -Recurse -File |
  Get-FileHash -Algorithm SHA256 |
  Select-Object Path, Hash
```

Record hashes in the deployment audit log before and after install.
