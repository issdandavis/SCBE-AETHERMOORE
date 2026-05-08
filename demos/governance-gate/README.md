# SCBE Governance Gate — Live Demos

Three demos. Pick the one your audience needs.

## 1. Browser demo (link-droppable)

`demos/governance-gate/index.html` — a single-page client-side demo of the
canonical Layer-12 harmonic-wall formula. No backend, no API key, drag the
folder onto Netlify or push to a GitHub Pages branch and you have a public
URL you can paste into a cold email.

```bash
# preview locally
python -m http.server 8000 --directory demos/governance-gate
# open http://localhost:8000
```

What the visitor sees:
- Five preset prompts (two benign, three adversarial)
- Live `d_H` (hyperbolic distance), `H` (harmonic score), and cost multiplier
- The Layer-13 verdict (ALLOW / QUARANTINE / ESCALATE / DENY) updating on
  every keystroke

The page is honest about what it's doing: distance is estimated from a
12-feature heuristic so the demo runs offline; the audited 14-layer pipeline
ships in the `scbe-agent-bus` packages.

### Deploy to GitHub Pages

```bash
git checkout --orphan gh-pages-governance-gate
git rm -rf .
cp -r demos/governance-gate/. .
git add . && git commit -m "deploy: governance-gate demo"
git push -u origin gh-pages-governance-gate
# then in repo Settings -> Pages, point Pages at this branch
```

## 2. Terminal demo (for the candidate who lives in zsh)

`scripts/demos/scbe_governance_terminal_demo.py` — the same canonical
formulas, color-coded, on stdin or a file.

```bash
python scripts/demos/scbe_governance_terminal_demo.py
python scripts/demos/scbe_governance_terminal_demo.py --prompts my_list.txt
echo "Ignore all previous instructions" | python scripts/demos/scbe_governance_terminal_demo.py -
```

The terminal demo and the browser demo agree on every preset prompt — they
share the same heuristic distance model. Useful when you want to show a
defense scout that the gate's verdict isn't a UI illusion.

## 3. Recruitment trial (for the technical-cofounder filter)

`scripts/demos/scbe_recruitment_trial.py` — a 4-phase, 90-minute trial
the candidate runs themselves.

| Phase | Test |
|------:|------|
| 1 | Run the terminal demo, confirm it produces both ALLOW and DENY |
| 2 | Implement `harmonic_scale(d, pd)` from scratch in `candidate/phase2_harmonic_scale.py` and match the canonical formula on five sample points |
| 3 | Hit the local `/v1/agents/dispatch` endpoint from `candidate/phase3_bus_call.py` and parse the verdict |
| 4 | Write a Markdown report (`candidate/phase4_adversarial_report.md`) reasoning about each tier of an adversarial set |

Self-grading. Prints `SCORE: N / 4`. The trial file's SHA-256 is printed at
the top of the run, so a candidate who edits the harness to fake a pass
leaves a trace.

```bash
# candidate runs:
python scripts/demos/scbe_recruitment_trial.py            # all 4 phases
python scripts/demos/scbe_recruitment_trial.py --phase 1  # individual
```

## Audited claims

The verdicts the demos render come from the same canonical Layer-12 formula
that ships in the npm and PyPI packages:

```
H(d, p_d) = 1 / (1 + d_H + 2 * p_d)        # in (0, 1]
cost(d)   = phi ^ (d_H ^ 2)                 # cost moat
```

Real audited numbers from this pipeline (see `tests/eval/`):
- 180 / 180 on the executable coding holdout — Wilson 95% CI [0.979, 1.0]
- 27 / 27 on role-pinned holographic-set retrieval — namespace SNR 41×
- 257 / 257 on cross-lane concept-preservation drift guard

The demos use a heuristic distance estimator so they run client-side; the
audited numbers above come from the full 14-layer pipeline server-side.

## Packages

```bash
npm i scbe-agent-bus       # Node side
pip install scbe-agent-bus # Python side
```
