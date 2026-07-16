# AAP Blend Probe

`aap-blend-probe` tests submission blend recipes across the sixteen provided
Autonomous Agent Prediction family datasets.

```powershell
node bin/geoseal.cjs aap-blend-probe --json
```

Default output:

```text
reports\aap_blend_probe.json
```

Current probe result from 2026-07-16:

```text
top2_rank70 mean AUC 0.7979
top2_mix    mean AUC 0.7979
top2_rank   mean AUC 0.7979
top2_raw    mean AUC 0.7979
top3_raw    mean AUC 0.7968
```

The current high-score AAP package is:

```text
C:\Users\issda\kaggle\aap\competition\submissions\scbe_tabular_v9_broad_select_20260716
```

It prioritizes `top2_rank70`, then the other top-2 variants, then top-3/raw
fallbacks and strong single models. This replaced the earlier v7 top-4 blend
assumption and v8's narrower six-submission cap.

Submit when the AAP slot is available:

```powershell
node bin/geoseal.cjs aap-package-submit `
  --agent-dir submissions/scbe_tabular_v9_broad_select_20260716 `
  --submit `
  --status `
  --message "scbe aap v9 broad select top2 plus singles" `
  --json
```
