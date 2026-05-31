# Terminal-Bench Live Run: 2026-05-31

## Environment

- Host path: `C:\Users\issda\SCBE-AETHERMOORE`
- Working run surface: WSL2 `Ubuntu-24.04`
- Python: `3.12.3`
- Terminal-Bench: `0.2.18`
- Container surface: Podman `4.9.3`, Docker CLI `29.1.3`, `/run/podman/podman.sock`
- SCBE commit recorded by smoke harness: `e627e9390cff992b25261fdf785435037d9d57fe`

Windows `tb` under Python 3.14 currently fails before help output with a Typer/Python annotation error. Public runs should use WSL2 Python 3.12.

## Neutral Packet

Command:

```powershell
python scripts/benchmark/tb_neutral_compare.py --mode run --tasks hello-world,fix-permissions,openssl-selfsigned-cert,broken-python,fibonacci-server,fix-pandas-version,grid-pattern-transform,csv-to-parquet,heterogeneous-dates,fix-git,sanitize-git-repo,nginx-request-logging,polyglot-c-py --max-turns 20 --json
```

Result:

| Agent | Resolved | Total | Accuracy |
| --- | ---: | ---: | ---: |
| Oracle | 13 | 13 | 100% |
| SCBE governed agent | 13 | 13 | 100% |

Artifacts:

- Oracle: `artifacts/benchmarks/tb-neutral-compare/20260531T194820Z/oracle/2026-05-31__12-48-24/results.json`
- SCBE: `artifacts/benchmarks/tb-neutral-compare/20260531T194820Z/scbe/2026-05-31__12-58-04/results.json`

Claim boundary:

This is official terminal-bench task execution against the local `terminal-bench-core-0.1.1` task set. It proves SCBE governance did not reduce completion on this neutral packet. It is not a Terminal-Bench 2.x public leaderboard row.

## Hard Security-Terminal Probe

Command:

```powershell
python scripts/benchmark/tb_neutral_compare.py --mode run --tasks crack-7z-hash,decommissioning-service-with-sensitive-data --max-turns 20 --json
```

Result:

| Agent | Resolved | Total | Accuracy |
| --- | ---: | ---: | ---: |
| Oracle | 2 | 2 | 100% |
| SCBE governed agent | 0 | 2 | 0% |

Artifacts:

- Oracle: `artifacts/benchmarks/tb-neutral-compare/20260531T200702Z/oracle/2026-05-31__13-07-08/results.json`
- SCBE: `artifacts/benchmarks/tb-neutral-compare/20260531T200702Z/scbe/2026-05-31__13-11-22/results.json`
- SCBE governance logs:
  - `artifacts/benchmarks/tb-neutral-compare/20260531T200702Z/scbe/2026-05-31__13-11-22/crack-7z-hash/crack-7z-hash.1-of-1.2026-05-31__13-11-22/agent-logs/scbe_governance.json`
  - `artifacts/benchmarks/tb-neutral-compare/20260531T200702Z/scbe/2026-05-31__13-11-22/decommissioning-service-with-sensitive-data/decommissioning-service-with-sensitive-data.1-of-1.2026-05-31__13-11-22/agent-logs/scbe_governance.json`

Observed SCBE failure mode:

- `governance_summary`: `allow=0`, `quarantine=0`, `deny=0`, `polymerized_events=0`
- `commands`: `[]`
- debug:
  - `t1:cmds=0 done=False rat='json-parse-error'`
  - `t2:cmds=0 done=True rat='deterministic-fallback complete'`

Interpretation:

The hard probe failure was not a governance block. The agent did not produce executable commands for either task, so no governance decision fired. This is an agent/planner/model capability gap on harder terminal-security tasks.

## Public Wording

Use:

> SCBE matched the oracle on 13/13 neutral Terminal-Bench core tasks with governance enabled. On a two-task hard security-terminal probe, the oracle solved 2/2 and SCBE solved 0/2 because the current SCBE agent emitted no commands after JSON-parse failure. This cleanly separates governance overhead from planner capability.

Do not use:

> SCBE beats frontier agents.

That requires an unchanged public benchmark leaderboard run or a controlled public side-by-side with all raw artifacts published.
