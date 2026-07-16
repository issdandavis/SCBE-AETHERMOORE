# AAP Family Probe

`aap-family-probe` scores local model recipes against the sixteen provided
Autonomous Agent Prediction meta-datasets. It is not a Kaggle submission. It is
the local evidence gate used before building a new agent package.

```powershell
node bin/geoseal.cjs aap-family-probe --json
```

Default output:

```text
reports\aap_family_probe.json
```

Current probe result from 2026-07-16:

```text
hgb  mean AUC 0.7923
lgbm mean AUC 0.7897
rf   mean AUC 0.7816
et   mean AUC 0.7654
lr   mean AUC 0.7313
```

The v7 agent should therefore prioritize HGB/LGBM with RF/LR/ET as diversity
candidates, then let the AAP public score select the best in-session submission.
