# Clay VQCC read-only Kaggle intake release

This is a prepared-only, private, internet-disabled, CPU packet for the exact
`issacizrealdavis/clay-vqcc-research-corpus/2` source. The explicit `/2` is
required because the dataset's current default is newer. It discovers the mount by the
exact `CORPUS_MANIFEST.json` SHA-256, reruns the reviewed source-family split and
bounded task sampling under `/tmp`, and persists only an atomic bounded archive
plus a terminal receipt.

The committed packet is intentionally launch-disabled. `EXECUTION_ADMISSION.json`
must remain `NOT_CONSUMED` / `execution_authorized: false` until a separate,
one-use authorization is issued and the packet manifest is regenerated. There
is no training, model load, dataset mutation, verifier run, circuit generation,
competition submission, or checkpoint promotion in this release.

Kaggle CLI 2.2.5 uploads only the configured `code_file`, so the release builds
`clay_vqcc_readonly_intake.py` as a self-contained script. It embeds a
deterministic compressed payload of the reviewed modules, spec, metadata, and
admission, verifies every embedded SHA-256, and materializes them only in a
fresh temporary runtime directory. The isolated smoke test executes with only
that one generated file present.

Local verification:

```powershell
python prepare_release.py --output <fresh-path>
python verify_release.py
python -m pytest -q test_release.py
```
