# System Variable Tuning Policy

Tune variables after the first baseline run using `summary.json`.

## Input Metrics

- `allowed_records`
- `quarantined_records`
- `audit_status`
- `core_health_passed`

Derived:

- `quarantine_ratio = quarantined_records / (allowed_records + quarantined_records)`

## Threshold Variables (cloud kernel config)

Path: `training/cloud_kernel_pipeline.json` under `thresholds`.

- `truth_min`
- `useful_min`
- `harmful_max`
- `dataset_anomaly_threshold`
- `dataset_max_flagged_ratio`

## Runtime Variables (profile)

Path: `training/internet_workflow_profile.json` under `web_research`.

- `max_tabs`
- `max_per_topic`
- `skip_core_check`

## Policy Bands

- `hard-tighten`
  - Trigger: `core_health_passed=false` OR `audit_status!=ALLOW` OR `quarantine_ratio > 1.5 * target`.
  - Action: tighten thresholds aggressively, reduce runtime concurrency.
- `tighten`
  - Trigger: `target < quarantine_ratio <= 1.5 * target`.
  - Action: tighten thresholds moderately, reduce runtime concurrency slightly.
- `relax`
  - Trigger: `core_health_passed=true` AND `audit_status=ALLOW` AND `quarantine_ratio < 0.5 * target`.
  - Action: relax thresholds slightly, increase throughput slightly.
- `steady`
  - Trigger: all other cases.
  - Action: keep values unchanged.

## Bounds

- `truth_min`: `[0.55, 0.90]`
- `useful_min`: `[0.50, 0.88]`
- `harmful_max`: `[0.08, 0.35]`
- `dataset_anomaly_threshold`: `[0.60, 0.90]`
- `dataset_max_flagged_ratio`: `[0.03, 0.15]`
- `max_tabs`: `[2, 12]`
- `max_per_topic`: `[3, 12]`

## Safety Rule

If health or audit fails, force `skip_core_check=false` in tuned profile.

