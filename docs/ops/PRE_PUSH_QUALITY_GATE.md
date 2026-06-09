# SCBE Pre-Push Quality Gate

Use this before pushing code-bearing changes.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/pre_push_quality_gate.ps1
```

For the full CLI suite:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/pre_push_quality_gate.ps1 -FullCli
```

After pushing, wait for GitHub Actions and fail fast if the latest run does not pass:

```powershell
git push origin <branch>
powershell -ExecutionPolicy Bypass -File scripts/system/pre_push_quality_gate.ps1 -SkipTests -WaitForGithub -Branch <branch>
```

## What The Gate Checks

- `git diff --check` for whitespace, conflict marker, and malformed diff issues.
- CLI JavaScript syntax checks.
- Prettier over the CLI benchmark surface and benchmark target registry.
- Targeted CLI benchmark tests by default, or the full CLI suite with `-FullCli`.
- Harness matrix smoke.

## Agent Rule

Do not treat a pushed branch as finished until:

1. Local gate passed.
2. Push completed.
3. GitHub Actions attempted the branch.
4. The latest run was checked manually.
5. Any CI failure was reproduced or triaged locally before another push.

This is a guardrail against the recurring pattern where formatting, spacing, character escaping, or generated-file noise lands in GitHub and fails later.
