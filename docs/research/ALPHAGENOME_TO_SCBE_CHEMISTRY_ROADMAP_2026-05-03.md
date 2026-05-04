# AlphaGenome To SCBE Chemistry Roadmap - 2026-05-03

## Purpose

AlphaGenome is useful to SCBE as a pattern, not as a chemistry model. Its public
surface shows a disciplined science-agent shape:

1. accept a structured biological input,
2. make multimodal predictions,
3. expose fine-grained effect outputs,
4. keep examples, documentation, and client code reproducible,
5. bind use to terms, scale limits, and citation expectations.

SCBE should copy that operating shape for chemistry while keeping the chemistry
math and governance local.

## AlphaGenome Pattern To Reuse

| AlphaGenome Pattern | SCBE Chemistry Equivalent |
|---|---|
| DNA interval and variant input | SMILES, reaction string, catalyst, solvent, pH, light, temperature, or workflow packet |
| Output modalities such as expression, splicing, chromatin, and contact maps | Validity, valence pressure, electronegativity tension, functional group, reaction class, conservation, toxicity or safety hold |
| Single-base-pair resolution where available | Atom, bond, token, and packet-slot resolution |
| Tutorials and example notebooks | Deterministic SFT rows, verifier scripts, Kaggle smoke rounds, and GeoSeal command-line examples |
| API key and terms boundary | Environment-gated connector use, public/free data first, no raw key logging, no unreviewed commercial claim |
| Benchmark-backed model statement | Gate-backed SCBE statement: pass rate, invalid molecule rejection, conservation checks, and harness receipts |

## Current SCBE Chemistry Assets

| Surface | Role |
|---|---|
| `python/scbe/state9d_chemistry.py` | Deterministic no-RDKit SMILES descriptor and 9D state mapping. |
| `python/scbe/state9d_chemistry_fusion.py` | SMILES to atomic token states, chemical fusion, and 9D governance summary. |
| `training-data/chemistry_manual_verification_v1.jsonl` | Manual chemistry obstacle course with valence, electronegativity, functional group, and bond checks. |
| `scripts/eval/verify_chemistry_manual.py` | RDKit-backed verifier for the manual chemistry dataset. |
| `scripts/eval/run_moses_benchmark_v2.py` | Molecule-generation benchmark lane against MOSES-style validity and novelty checks. |
| `scripts/build_chemistry_primary_sft.py` | Existing chemistry-primary drill extractor for Sacred Tongues transport rows. |
| `scripts/training_data/build_chemistry_manual_verification_sft.py` | Manual-verification SFT builder that teaches the full predict, verify, receipt, promote path. |
| `config/model_training/chemistry-qwen-primary.json` | Chemistry-only training profile. |
| `config/model_training/aligned-foundations-qwen-primary.json` | Cross-lane profile for mathematics, English, Sacred Tongues, binary transport, chemistry, and coding. |

## Roadmap

### Stage C1 - Verification First

Goal: make chemistry correctness observable before trying to generate better
molecules.

Required gates:

- RDKit validity or explicit invalid rejection.
- Manual atom and bond arithmetic.
- Functional group match.
- Electronegativity and polarity explanation.
- SCBE fusion state finite and in expected ranges.
- Governance verdict agrees with chemistry validity.

Current command:

```powershell
python scripts/eval/verify_chemistry_manual.py
```

### Stage C2 - Training Rows From Manual Arithmetic

Goal: train the model to show the chemical path, not just return labels.

Current command:

```powershell
python scripts/training_data/build_chemistry_manual_verification_sft.py --copy-kaggle --json
```

This emits:

- `training-data/sft/chemistry_manual_verification_v1_train.sft.jsonl`
- `training-data/sft/chemistry_manual_verification_v1_eval.sft.jsonl`
- `training-data/sft/chemistry_manual_verification_v1_sft_manifest.json`

### Stage C3 - Conservation And Reaction Packets

Goal: move from molecule verification to reaction verification.

Add rows shaped as:

```text
reactants + reagents + conditions -> predicted product + byproducts + conservation receipt
```

Required checks:

- atom conservation,
- charge conservation,
- allowed reagent role,
- plausible functional group transformation,
- blocked unsafe synthesis detail when required,
- source citation for public chemistry facts.

### Stage C4 - Generator Separate From Verifier

Goal: avoid confusing molecule generation quality with chemistry governance.

Keep two separate scoreboards:

- generator score: validity, novelty, uniqueness, scaffold diversity;
- verifier score: correctness, conservation, invalid rejection, explanation fidelity.

The current MOSES result says the verifier/state engine is ahead of the
generator. That is acceptable. Train the generator only after the verifier is
strong enough to filter it.

### Stage C5 - AlphaGenome-Style Connector Probe

Goal: add genomics as a neighboring science lane without mixing it into
chemistry claims.

Use the optional fail-soft probe:

```powershell
python scripts/system/alphagenome_probe.py --json
```

The probe should check only:

- whether the package can import,
- whether an API key is present,
- whether terms/cost gates are acknowledged,
- whether the route is ready for a future tiny non-commercial fixture.

No AlphaGenome output should become training data unless its license and terms
allow that use.

## Benchmark Claim Boundary

Safe claim:

> SCBE uses AlphaGenome-like science-agent discipline for chemistry: structured
> inputs, multimodal outputs, deterministic receipts, verifier gates, and
> explicit promotion rules.

Do not claim:

- SCBE outperforms AlphaGenome.
- AlphaGenome is a chemistry model.
- SCBE has solved molecule generation.
- API outputs are open training data without checking terms.

## Next Practical Push

1. Expand `chemistry_manual_verification_v1` from 20 rows to 50-200 rows.
2. Add reaction conservation rows.
3. Run manual SFT plus chemistry-primary in a small chemistry-only training job.
4. Use `verify_chemistry_manual.py` and MOSES validity as separate gates.
5. Promote only the adapter that improves verifier pass rate without increasing
   invalid chemistry confidence.

## Sources

- Google DeepMind AlphaGenome blog: https://deepmind.google/blog/alphagenome-ai-for-better-understanding-the-genome/
- AlphaGenome GitHub repository: https://github.com/google-deepmind/alphagenome
- AlphaGenome installation documentation: https://www.alphagenomedocs.com/installation.html
