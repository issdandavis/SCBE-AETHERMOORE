# Follow an SCBE claim through Lean

Lean separates four things that ordinary prose often blends together:

1. The human claim says what we intend.
2. The theorem statement says exactly what is being checked.
3. The proof constructs evidence for that exact statement.
4. Lean's small kernel checks the construction and reports its axioms.

Open [`SCBE/ProofLab.lean`](SCBE/ProofLab.lean) beside this page. The first
example says that an aggregate containing `DENY` cannot equal `ALLOW`:

```lean
theorem deny_member_blocks_allow (checks : List SCBE.Decision)
    (hdeny : SCBE.Decision.deny ∈ checks) : SCBE.aggregate checks ≠ .allow := by
```

Everything before `:= by` is the claim. Everything after it is the proof. Put
the cursor after a proof line to see the remaining goal. Ctrl-click a name such
as `SCBE.aggregate_allow_iff` to open the theorem being reused. Hovering a name
shows its type, which is the contract Lean actually checks.

The file also contains:

- `#check`, which displays an expression's type;
- `#print`, which shows the elaborated declaration; and
- `#print axioms`, which shows the trusted assumptions beneath a theorem.

At the bottom is a deliberately false example kept inside a comment. Uncomment
it and Lean rejects the file because combining `DENY` with `ALLOW` does not
weaken the denial. Re-comment it to restore the build. This is a useful first
experiment because the failure is expected and understandable.

## Start in Codespaces

After this configuration is on the target branch, open:

[Create the SCBE Lean proof-lab Codespace](https://codespaces.new/issdandavis/SCBE-AETHERMOORE?quickstart=1&devcontainer_path=.devcontainer%2Flean-proof%2Fdevcontainer.json)

The container installs the repository's pinned Lean toolchain, downloads only
the Mathlib modules this project needs, builds all contracts, audits theorem
axioms, and confirms that the three false fixtures are rejected. Its validation
receipt is written under `~/.cache/scbe-lean-proof`, outside the Git worktree.

From `formal/lean`, the short feedback loop is:

```sh
lake build
python -X utf8 verify.py --output ~/.cache/scbe-lean-proof/manual-validation.json
```

Choose a new receipt filename for each full verification because the verifier
intentionally refuses to overwrite evidence.

## Why use the fork

`lakefile.toml` points to `issdandavis/mathlib4` at the exact commit
`c44e0c8ee63ca166450922a373c7409c5d26b00b`, which is Mathlib v4.19.0. The
commit hash—not a moving branch name—is the dependency identity. Your fork can
therefore be explored in its own Codespace while SCBE stays reproducible.

The fork supplies the mathematical library. SCBE theorem files remain in this
repository so a future Mathlib sync cannot silently rewrite the claims being
proved.
