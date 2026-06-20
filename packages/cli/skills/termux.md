# Termux Skill Card

summary: Prepare SCBE CLI work for Android Termux without assuming Windows PowerShell.
triggers: termux, termunx, android, phone, mobile, pkg, apt, termux api

## Worksheet

- Translate Windows shell assumptions into POSIX-safe commands.
- Prefer `pkg update` and `pkg install nodejs git python` for first setup.
- Use `termux-api` only when the Termux:API app and package are installed.
- Keep heavy builds and native crypto optional; prefer receipts and remote fallbacks when the phone is resource-bound.
