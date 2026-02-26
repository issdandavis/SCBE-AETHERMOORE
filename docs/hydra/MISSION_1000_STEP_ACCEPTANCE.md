# HYDRA Mission 1000-Step Acceptance Spec

## Mission scope
This specification defines acceptance criteria for a synthetic 1000-step HYDRA swarm mission executed through `scripts/aetherbrowse_swarm_runner.py`.

## Required thresholds
- **Required step count:** `1000` total normalized actions across all jobs in the mission input.
- **Maximum failure rate:** `<= 1.0%` failed actions (`failed_actions / total_actions`).
- **Maximum duplicate-lock incidents:** `<= 2` duplicate page-lock collisions across the full mission run.

## Required audit artifacts
Every mission run MUST persist the following artifacts under artifact storage:

1. **Decision records (required):**
   - One DecisionRecord JSON per job.
   - Each record must include decision, verification score, risk metrics, and capability gate outcome.
2. **Trace hashes (required):**
   - A trace file per job containing request/response evidence.
   - A deterministic `trace_hash` persisted in both DecisionRecord and run summary.
3. **Run summary (required):**
   - Machine-readable pass/fail summary including:
     - total jobs
     - total actions
     - failed actions
     - failure rate
     - duplicate lock incidents
     - mission verdict

## Mission verdict rules
A run is marked **PASS** only if all conditions are true:
1. total normalized actions equals `1000`
2. failure rate is `<= 1.0%`
3. duplicate-lock incidents is `<= 2`
4. required audit artifacts are present and readable

Otherwise the run is marked **FAIL**.
