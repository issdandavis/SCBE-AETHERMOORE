# Usability Claims Ledger

Standards the packages already state. `measure.cjs` parses this table.
`surface` is `local` (packed from this tree) or `published` (registry tarball).

| package | surface | command | expected_exit | expected_stdout_match |
|---|---|---|---|---|
| scbe-aethermoore-cli | local | scbe selftest | 0 | scbe_aethermoore_cli_selftest_v1 |
| scbe-aethermoore-cli | local | scbe --help | 0 | scan |
| scbe-aethermoore-cli | local | scbe-task --help | 0 | do_not_promote_to_fact |
| scbe-aethermoore-cli | local | scbe version --json | 0 | scbe_aethermoore_cli_version_v1 |
| scbe-aethermoore | local | scbe-scan "clean text" | 0 | OK |
| scbe-aethermoore | local | scbe-scan --help | 0 | Usage |
| scbe-agent-bus | local | scbe-agent-bus --help | 0 | serve |
| scbe-polly-pad-cli | local | polly | 0 | init |
| scbe-polly-pad-cli | local | polly init | 0 | .polly |
| clay-system | local | clay doctor | 0 | Loom checkout |
| scbe-aethermoore-cli | published | scbe selftest | 0 | scbe_aethermoore_cli_selftest_v1 |
| scbe-aethermoore-cli | published | scbe --help | 0 | scan |
| scbe-aethermoore-cli | published | scbe-task --help | 0 | do_not_promote_to_fact |
| scbe-aethermoore-cli | published | scbe version --json | 0 | scbe_aethermoore_cli_version_v1 |
| scbe-aethermoore | published | scbe-scan "clean text" | 0 | OK |
| scbe-aethermoore | published | scbe-scan --help | 0 | Usage |
| scbe-agent-bus | published | scbe-agent-bus --help | 0 | serve |
| scbe-polly-pad-cli | published | polly | 0 | init |
| scbe-polly-pad-cli | published | polly init | 0 | .polly |
