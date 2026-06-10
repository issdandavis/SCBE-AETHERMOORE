# Runnable Ebook Format v1

Canonical schema for SCBE buyer-facing books. Every chapter is a markdown
file with a 5W frontmatter, prose body, fenced code blocks the reader can
actually run, and a paired test suite that proves the examples work today
on the published code path.

The format is the substrate for the M5 product line: governance ebooks,
training vault, hire-prep packets. It is also the substrate for HF model
training data — chapters become the gold ground truth.

Schema version: `scbe_runnable_ebook_v1`
First publication: 2026-05-10

---

## Why a runnable book

A static AI-governance ebook decays the day a library version bumps. A
runnable book carries its own evidence: the test suite proves every
example still works against the published SCBE code, and CI fails the
chapter if it does not. A reader can paste any code block into a fresh
shell and get the same output the chapter promises.

The 5Ws (Who, What, When, Where, Why) sit in the frontmatter so a
machine — Polly chat, an HF training pipeline, a search index — can
answer "who is this for and when do I read it" without parsing prose.

---

## File layout

```
book/
  <book-slug>/
    book.yaml               # book-level metadata (title, version, chapter index)
    chapter-NN-<slug>.md    # one chapter per file, NN is two digits
    assets/                 # images, datasets, optional notebooks/
tests/
  book/
    <book-slug>/
      test_chapter_NN_<slug>.py
notebooks/
  <book-slug>/
    chapter-NN.ipynb        # optional Colab/Jupyter mirror
```

Every chapter MUST have a paired test file. Every test file MUST have a
paired chapter file. The runnable-ebook validator (`tests/book/test_runnable_ebook_format.py`)
fails if either side is missing.

---

## Chapter frontmatter (the 5Ws)

```yaml
---
schema: scbe_runnable_ebook_v1
book: <book-slug>
chapter: <NN>                   # two-digit number, matches filename
slug: <kebab-case-slug>         # matches filename suffix
title: <human-readable title>
version: <semver>               # bumped per chapter on rewrite

# The 5Ws — required, machine-readable, single line each
who: <one-line target reader>
what: <one-line topic>
when: <one-line trigger>
where: <one-line system locus>
why: <one-line consequence>

# Pointers
test_suite: tests/book/<book-slug>/test_chapter_<NN>_<slug>.py
notebook: notebooks/<book-slug>/chapter-<NN>.ipynb   # optional
runnable_languages: [python]                          # python | typescript | both
estimated_read_minutes: <int>
prereq_chapters: []                                   # list of chapter numbers

# Optional — only if the chapter ships sample data
datasets: []                                          # list of paths under book/<slug>/assets/
---
```

### 5W definitions

| Field | Definition | Example |
|-------|------------|---------|
| **who** | Target reader role + experience level | "AI engineers shipping LLM-backed features for the first time" |
| **what** | Single-sentence topic claim | "How the SCBE harmonic wall H(d, pd) bounds adversarial cost" |
| **when** | The trigger that brings a reader to this chapter | "Before deploying any model that takes free-form user input" |
| **where** | Where in the system this belongs | "At the output gate, between model response and downstream caller" |
| **why** | The consequence of NOT knowing this | "Unbounded scoring lets attackers walk the threshold without paying cost" |

Each field is one line, ≤ 200 chars. Prose elaborations live in the body.

---

## Chapter body

The body MUST contain at least one fenced code block in a `runnable_languages`
language and at least one assertion. The extraction tool
(`scripts/book/extract_chapter_examples.py`) splits the body into:

- **Prose** — everything outside fenced code blocks
- **Examples** — fenced code blocks tagged `python` or `typescript`
- **Outputs** — fenced code blocks tagged `text` or `output` that follow an
  example block (treated as expected output for that example)

Every example is run by the chapter's test suite, which asserts:

1. The example imports succeed against the live SCBE package
2. Any `assert` inside the example does not raise
3. If an `output` block follows, the captured stdout matches it (whitespace-
   trimmed, line-by-line)

### Example body shape

````markdown
# The Harmonic Wall

Brief prose introducing the concept.

## Runnable example

```python
from scbe.harmonic import wall
score = wall(distance=0.3, prior_drift=0.05)
assert 0 < score <= 1
print(f"score = {score:.4f}")
```

```output
score = 0.7143
```

## What this proves

More prose tying the example to the bigger picture.
````

---

## Test suite contract

The paired test file MUST:

1. Import the chapter via `tests/book/_runner.py:run_chapter(book, NN)`
2. Run all extracted examples
3. Assert no example raises
4. If a chapter-level invariant is testable beyond the example assertions,
   add it as an extra `def test_<invariant>` in the same file

```python
# tests/book/ai-governance-fundamentals/test_chapter_01_harmonic_wall.py
from tests.book._runner import run_chapter

def test_chapter_01_examples_run() -> None:
    result = run_chapter("ai-governance-fundamentals", 1)
    assert result["examples_run"] >= 1
    assert result["examples_failed"] == 0

def test_chapter_01_safety_score_is_bounded() -> None:
    # Chapter-level invariant beyond the example
    from src.symphonic_cipher.scbe_aethermoore.concept_blocks.cstm.telemetry_bridge import HamiltonianTracker
    tracker = HamiltonianTracker()
    h = tracker.update([0.5] * 21, set())
    assert 0 < h <= 1
```

---

## Polly integration

Books are surfaced to Polly chat via the catalog endpoint. Each book ships
a `book.yaml` index Polly can read to answer "what's in chapter 3 of X" or
"which chapter is for someone deploying their first LLM."

A book-level "Try this notebook" action (the `notebook` frontmatter field)
becomes a chip in Polly's reply when the user asks for a demo.

---

## Pricing model implication

Each chapter is independently checkable, so books can ship at different
prices than monolithic toolkits:

- **Single-chapter sample** — free or $1, used as the entry point
- **Volume bundle** (5–10 chapters) — $19–$49, replaces the current $29
  toolkit/vault SKUs
- **Updates as a subscription** — $5/month for new chapters + bug-fixed
  examples, layered on top of a one-time bundle purchase

The actual price ladder is set in `api/polly/commerce.js`; the schema only
requires that each chapter advertise its standalone testability.

---

## Validation

The CI gate is two checks:

1. `npm run book:test` — runs every chapter's test suite
2. `pytest tests/book/test_runnable_ebook_format.py` — schema validator:
   every chapter has the 5W frontmatter, the named test_suite exists,
   chapter and test files are paired one-to-one

Either failure fails CI.

---

## Future versions

v2 will likely add:

- TypeScript runnable examples alongside Python
- Per-example output comparison (today only the chapter-level test asserts)
- A `since_version` field per chapter so reissued chapters can carry a
  changelog
- A signed manifest so paid bundles can be cryptographically delivered

v1 deliberately ships small. Until at least three chapters across two
books ship, the schema stays minimal.
