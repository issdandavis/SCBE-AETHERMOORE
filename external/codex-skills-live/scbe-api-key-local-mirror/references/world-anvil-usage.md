# World Anvil Usage with Local Mirror

## Store Key

If key is already in env:

```bash
python C:/Users/issda/.codex/skills/scbe-api-key-local-mirror/scripts/key_mirror.py store --service world_anvil --env WORLD_ANVIL_API_KEY
```

If key is not in env, run store without `--env` and paste at prompt:

```bash
python C:/Users/issda/.codex/skills/scbe-api-key-local-mirror/scripts/key_mirror.py store --service world_anvil
```

## Resolve Key for Current Session

```bash
python C:/Users/issda/.codex/skills/scbe-api-key-local-mirror/scripts/key_mirror.py resolve --service world_anvil --env-out WORLD_ANVIL_API_KEY
```

Copy the `powershell` line from JSON output, run it, then use your World Anvil request script/curl call.

## Note About GitHub Secrets

GitHub Actions secret values cannot be read back via API/UI after save.
You must provide the key from original source once to seed local mirror.
