# AAP GeoSeal Package Guard

This guard wraps the Autonomous Agent Prediction submission workflow:

1. Run the official validator.
2. Build a root-correct `submission.zip`.
3. Check that `agent.yaml` is at archive root.
4. Optionally submit through Kaggle CLI.
5. Write a receipt.

## Validate and package

```powershell
node bin/geoseal.cjs aap-package-submit `
  --agent-dir submissions/scbe_tabular_v3_skillroot_20260716 `
  --json
```

## Validate, package, submit, and read status

```powershell
node bin/geoseal.cjs aap-package-submit `
  --agent-dir submissions/scbe_tabular_v3_skillroot_20260716 `
  --submit `
  --status `
  --message "scbe tabular auc v3 skillroot validated root zip" `
  --json
```

## Defaults

- Competition dir: `C:\Users\issda\kaggle\aap\competition`
- Competition slug: `autonomous-agent-prediction-beta`
- Receipt: `reports\aap_package_submit_receipt.json`

The guard exists because the Kaggle API accepts an uploaded zip stream before
rejecting malformed archive layout. The important invariant is:

```text
submission.zip
  agent.yaml
  prompts/
  configs/
  skills/
```

not:

```text
submission.zip
  agent/
    agent.yaml
```
