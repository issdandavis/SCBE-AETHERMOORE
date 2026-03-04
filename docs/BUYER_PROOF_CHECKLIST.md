# Buyer Proof Checklist

Use this checklist before presenting SCBE automation to a buyer.

## 1. Execution Proof

- [ ] Governed browser run completed
- [ ] `artifacts/evidence_packs/<run_id>/scorecard.json` exists
- [ ] `artifacts/evidence_packs/<run_id>/README.md` exists
- [ ] Decision records exist under run artifacts
- [ ] Trace files exist under run artifacts

## 2. Governance Proof

- [ ] High-risk actions require capability token
- [ ] Verification scoring is present for every job
- [ ] Final decisions include ALLOW/QUARANTINE/DENY/NOISE
- [ ] No silent failures in summary report

## 3. Training Proof

- [ ] `hf_training_metrics.json` exists in training run folder
- [ ] `growth_monitor_report.json` exists
- [ ] Growth is confirmed (accuracy up or loss down)
- [ ] Label coverage and sample count are reported

## 4. Operability Proof

- [ ] One command can rerun evidence pack build
- [ ] One command can rerun training
- [ ] One command can rerun growth monitor

## 5. Buyer-Ready Summary

- [ ] Pilot scope documented (`docs/OFFER_PILOT.md`)
- [ ] Evidence paths included in handoff note
- [ ] Pass/fail criteria clearly stated

