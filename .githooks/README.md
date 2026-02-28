# SCBE Git Hooks

Enable repo-local hooks:

```bash
git config core.hooksPath .githooks
chmod +x .githooks/pre-push
```

The `pre-push` hook runs `scripts/system/full_system_smoke.py` and blocks pushes if required stack checks fail.

Override (one push only):

```bash
SCBE_SKIP_STACK_SMOKE=1 git push
```
