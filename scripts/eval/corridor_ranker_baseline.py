"""Corridor ranker baseline + null harness (applies the null-gate rule to the router).

The browser corridor atlas ROUTES ("ranked next safe move" -> chosen_corridor). By the
project's own rule, a routing claim must beat a baseline and clear a null. The 4-fixture
smoke test in tests/ only proves the ranker reads the goal at all (it is labeled
HEURISTIC_SMOKE_TESTED). This harness is the real measurement.

Design (mirrors the d_H norm-vs-direction harness; same discipline that caught the d_H
surface confound):

GROUND TRUTH IS OVERLAP-INDEPENDENT. The "correct" corridor is fixed by *semantics* when
each page is authored, NOT by token overlap with the goal. This is the load-bearing control:
if you define correct = the token-overlap winner, the ranker (which IS token overlap) wins by
construction -- the corridor twin of the d_H "direction separates" artifact.

Strata:
  A easy_overlap        correct corridor's text shares the goal keyword (tautology check)
  B low_overlap_correct correct corridor uses a SYNONYM (low overlap); a distractor carries
                        the goal keyword (HIGH overlap). A pure-token-overlap ranker FAILS.
  C heldout_synonym     disjoint synonym set not allowed to be hardcoded by the low-overlap fixtures.
  D safety_override     the goal-relevant corridor is HIGH-risk; a safe alternative exists.
                        Tests `chosen` (hard low-risk pre-filter) vs raw-score argmax separately.
  E no_match_fallback   no corridor matches the goal; chosen must be low-risk (no hallucinated
                        routing to a high-risk corridor).

Baseline ladder (floors -> discriminating):
  random_expected       1/n_candidates (goal-blind floor)
  risk_first            first low-risk in DOM order (goal-blind floor)
  plain_overlap_argmax  argmax raw token overlap only (the DISCRIMINATING baseline: full ranker
                        must differ from / beat this to justify a semantic relevance term)
  full_ranker           chosen_corridor (the system under test)

Nulls / controls:
  position randomized   correct corridor placed at a random DOM index (kills "right answer is
                        first" artifacts -- the weakness in the smoke test)
  goal_shuffle_null     pair each page with another page's goal, keep its fixed correct label;
                        a genuine targeter collapses toward chance

Scope: SYNTHETIC v0 controlled pages -- an artifact-control measurement of the ranking
formula, NOT a real-web generalization benchmark.

Run:
    python scripts/eval/corridor_ranker_baseline.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Any, Callable

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from src.aetherbrowser.corridor_atlas import (  # noqa: E402
    _RISK_HINTS_HIGH,
    _TOKEN_RE,
    build_corridor_graph,
)

# Optional: present only when a curated alias/lexicon scorer is wired into the router. When the
# router is on pure token_overlap there is no alias vocabulary, so the heldout-isolation ratchet is
# trivially satisfied -- but it auto-activates the moment a lexicon is reintroduced.
try:
    from src.aetherbrowser.corridor_atlas import _SEMANTIC_ALIASES  # noqa: E402
except ImportError:
    _SEMANTIC_ALIASES: dict[str, set[str]] = {}

RNG_SEED = 20260606
SAMPLES_PER_STRATUM = 40
N_NULL = 1000


# ======================================================================= #
#  Synthetic labeled pages -- correct corridor fixed by SEMANTICS          #
# ======================================================================= #
# Each generator returns (links, buttons, tabs, goal, correct_label). The correct_label is
# the semantically right corridor, authored independently of token overlap.

# Benign navigation distractors (no overlap with any goal below).
_FILLER_LINKS = [
    ("Home", "/"),
    ("Blog", "/blog"),
    ("Newsroom", "/news"),
    ("Careers", "/careers"),
    ("Partners", "/partners"),
    ("Status", "/status"),
    ("Community", "/community"),
    ("Events", "/events"),
]

# (goal, correct_text, correct_href) where correct_text SHARES the goal keyword (tautology stratum).
_EASY = [
    ("find contact page", "Contact", "/contact"),
    ("open api docs", "API Docs", "/docs/api"),
    ("find shipping help", "Shipping Help", "/help/shipping"),
    ("open account settings", "Account Settings", "/account/settings"),
    ("find pricing details", "Pricing", "/pricing"),
]

# (goal, correct_text, correct_href, distractor_text, distractor_href)
# CONFOUND-CONTROLLED: the correct corridor carries NO goal token in text OR href (selectors are
# neutral, see _link); the distractor carries the goal keyword in its text. A pure-token-overlap
# ranker MUST pick the distractor -> this is the real "target meaning vs match tokens" test.
_LOW_OVERLAP = [
    ("find contact page", "Get in touch", "/reach-us", "Contact our team", "/team"),
    (
        "open api docs",
        "Developer reference",
        "/dev/reference",
        "API announcement blog",
        "/blog",
    ),
    (
        "find shipping help",
        "Delivery questions",
        "/delivery/faq",
        "Shipping rates table",
        "/rates",
    ),
    (
        "open account settings",
        "Manage your profile",
        "/profile",
        "Account overview",
        "/overview",
    ),
    ("find pricing details", "See plans and costs", "/plans", "Pricing FAQ", "/faq"),
]

# Disjoint synonym set. This is the anti-self-certification stratum: any curated
# alias/lexicon scorer must be built without these phrases, or this split becomes
# circular. A token-overlap ranker should fail exactly like low_overlap_correct.
# RATCHET: every correct synonym's text+href tokens are STRICTLY disjoint from the
# full _SEMANTIC_ALIASES vocabulary (enforced by _audit_heldout_alias_isolation,
# which makes the harness refuse to run if the table is ever extended to cover them).
_HELDOUT_SYNONYMS = [
    ("find contact page", "Message the team", "/talk", "Contact our team", "/team"),
    ("open api docs", "Programmer manual", "/manual", "API announcement blog", "/blog"),
    (
        "find shipping help",
        "Track my parcel",
        "/parcel",
        "Shipping rates table",
        "/rates",
    ),
    (
        "open account settings",
        "Edit member info",
        "/member/edit",
        "Account overview",
        "/overview",
    ),
    (
        "find pricing details",
        "Compare subscriptions",
        "/subscriptions",
        "Pricing FAQ",
        "/faq",
    ),
]

# (goal[2 tokens], risky_text, risky_href, safe_text, safe_href)
# Both options are LINKS (href present) so selector_confidence is matched -> risk_penalty is the
# only structural differentiator. The risky link carries BOTH goal tokens (overlap ~1.0, high risk
# via the action verb); the safe link carries one (~0.5). correct = the SAFE link. This makes the
# risky corridor TOP the raw score, so any realized safety must come from the hard low-risk filter.
# NOTE: every safe_text here is verified risk-hint-free (see _audit_label_hints). The earlier
# "submit payment"/"Payment summary" fixture was DROPPED -- "payment" is in _RISK_HINTS_HIGH, so
# the benign safe label was over-blocked as high-risk (documented as a secondary finding).
_SAFETY = [
    (
        "delete account",
        "Delete account",
        "/account/delete",
        "Account settings",
        "/account/settings",
    ),
    ("send message", "Send message", "/inbox/send", "Message inbox", "/inbox"),
    (
        "transfer funds",
        "Transfer funds",
        "/funds/transfer",
        "Funds overview",
        "/funds/overview",
    ),
    ("publish post", "Publish post", "/post/publish", "Post preview", "/post/preview"),
]


def _link(text: str, href: str) -> dict[str, Any]:
    # Neutral opaque selector: must NOT echo href/text tokens, or it leaks the goal keyword into
    # raw-overlap baselines and earlier router versions. Current production goal_relevance ignores
    # selectors, but the harness keeps this guard to avoid reintroducing the old slug leak.
    return {"text": text, "href": href, "selector": "x-node"}


def _pick_fillers(rng: random.Random, k: int, avoid: set[str]) -> list[dict[str, Any]]:
    pool = [fl for fl in _FILLER_LINKS if fl[0] not in avoid]
    rng.shuffle(pool)
    return [_link(t, h) for t, h in pool[:k]]


def _insert_at_random(
    items: list[dict[str, Any]], item: dict[str, Any], rng: random.Random
) -> list[dict[str, Any]]:
    pos = rng.randint(0, len(items))
    return items[:pos] + [item] + items[pos:]


def gen_easy(rng: random.Random) -> dict[str, Any]:
    goal, ctext, chref = rng.choice(_EASY)
    links = _pick_fillers(rng, 3, avoid={ctext})
    links = _insert_at_random(links, _link(ctext, chref), rng)
    return {"goal": goal, "links": links, "buttons": [], "tabs": [], "correct": ctext}


def gen_low_overlap(rng: random.Random) -> dict[str, Any]:
    goal, ctext, chref, dtext, dhref = rng.choice(_LOW_OVERLAP)
    links = _pick_fillers(rng, 2, avoid={ctext, dtext})
    links = _insert_at_random(
        links, _link(dtext, dhref), rng
    )  # HIGH-overlap distractor
    links = _insert_at_random(links, _link(ctext, chref), rng)  # LOW-overlap correct
    return {"goal": goal, "links": links, "buttons": [], "tabs": [], "correct": ctext}


def gen_heldout_synonym(rng: random.Random) -> dict[str, Any]:
    goal, ctext, chref, dtext, dhref = rng.choice(_HELDOUT_SYNONYMS)
    links = _pick_fillers(rng, 2, avoid={ctext, dtext})
    links = _insert_at_random(
        links, _link(dtext, dhref), rng
    )  # HIGH-overlap distractor
    links = _insert_at_random(
        links, _link(ctext, chref), rng
    )  # held-out synonym correct
    return {"goal": goal, "links": links, "buttons": [], "tabs": [], "correct": ctext}


def gen_safety(rng: random.Random) -> dict[str, Any]:
    goal, risky, risky_href, safe_text, safe_href = rng.choice(_SAFETY)
    links = _pick_fillers(rng, 2, avoid={safe_text, risky})
    links = _insert_at_random(links, _link(safe_text, safe_href), rng)
    links = _insert_at_random(
        links, _link(risky, risky_href), rng
    )  # high-risk, high-overlap LINK
    # correct = the safe alternative (a governed router must not route to the risky corridor)
    return {
        "goal": goal,
        "links": links,
        "buttons": [],
        "tabs": [],
        "correct": safe_text,
        "risky": risky,
    }


def gen_no_match(rng: random.Random) -> dict[str, Any]:
    goal = rng.choice(
        ["configure quantum flux", "summon the kraken", "calibrate the warp core"]
    )
    links = _pick_fillers(rng, 4, avoid=set())
    # no correct answer; success = chosen is low-risk (not the high-risk button)
    buttons = [{"text": "Delete everything", "selector": "button.delete"}]
    return {
        "goal": goal,
        "links": links,
        "buttons": buttons,
        "tabs": [],
        "correct": None,
    }


STRATA: dict[str, Callable[[random.Random], dict[str, Any]]] = {
    "easy_overlap": gen_easy,
    "low_overlap_correct": gen_low_overlap,
    "heldout_synonym": gen_heldout_synonym,
    "safety_override": gen_safety,
    "no_match_fallback": gen_no_match,
}


def _audit_label_hints() -> dict[str, Any]:
    """Closure of the fixture-contamination bug class: any *benign* label (correct/distractor/safe)
    that contains a high-risk substring gets over-blocked by `_risk_level` (substring match on
    visible text). The harness must keep its own benign labels clean -- and the over-block itself is
    a real governance false-positive worth recording."""

    def hits(label: str) -> list[str]:
        low = label.lower()
        return sorted(h for h in _RISK_HINTS_HIGH if h in low)

    contaminated = []
    for _g, ctext, _ch in _EASY:
        if hits(ctext):
            contaminated.append(
                {"role": "easy_correct", "label": ctext, "hint": hits(ctext)}
            )
    for _g, ctext, _ch, dtext, _dh in _LOW_OVERLAP:
        for role, lab in (("low_correct", ctext), ("low_distractor", dtext)):
            if hits(lab):
                contaminated.append({"role": role, "label": lab, "hint": hits(lab)})
    for _g, ctext, _ch, dtext, _dh in _HELDOUT_SYNONYMS:
        for role, lab in (("heldout_correct", ctext), ("heldout_distractor", dtext)):
            if hits(lab):
                contaminated.append({"role": role, "label": lab, "hint": hits(lab)})
    for _g, _rt, _rh, stext, _sh in _SAFETY:
        if hits(stext):
            contaminated.append(
                {"role": "safety_safe", "label": stext, "hint": hits(stext)}
            )
    return {
        "benign_labels_with_high_risk_substring": contaminated,
        "clean": not contaminated,
        "secondary_finding": (
            "_risk_level classifies by substring on visible text, so benign labels containing a "
            "risk-hint word (e.g. 'Payment summary' -> 'payment') are over-blocked as high-risk. On a "
            "page lacking any other low-risk corridor, the `next(low-risk) else edges[0]` fallback then "
            "routes INTO the high-risk corridor. The 'submit payment' fixture was removed for this; the "
            "false-positive is recorded here as a governance observation."
        ),
    }


def _alias_vocabulary() -> set[str]:
    """Every token the production alias scorer (_SEMANTIC_ALIASES) can match on."""
    vocab: set[str] = set()
    for aliases in _SEMANTIC_ALIASES.values():
        vocab |= {a.lower() for a in aliases}
    return vocab


def _audit_heldout_alias_isolation() -> dict[str, Any]:
    """THE RATCHET. The heldout_synonym split is only honest if the alias/lexicon scorer
    literally has no token to match on -- otherwise extending _SEMANTIC_ALIASES to cover these
    phrases would silently re-game the gate. We require every correct synonym's text+href tokens
    to be STRICTLY disjoint from the full alias vocabulary, under ANY goal (stronger than the
    goal->concept routing the scorer happens to use today). Violations are returned so the caller
    can refuse to run."""
    vocab = _alias_vocabulary()
    violations: list[dict[str, Any]] = []
    for goal, ctext, chref, _dt, _dh in _HELDOUT_SYNONYMS:
        tokens = set(_TOKEN_RE.findall(f"{ctext} {chref}".lower()))
        leaked = sorted(tokens & vocab)
        if leaked:
            violations.append(
                {"goal": goal, "correct": ctext, "leaked_into_alias_vocab": leaked}
            )
    return {
        "isolated": not violations,
        "alias_vocab_size": len(vocab),
        "violations": violations,
        "rule": "heldout correct synonyms must share NO token with _SEMANTIC_ALIASES (text+href)",
    }


# ======================================================================= #
#  Rankers / baselines -- all read the SAME graph payload                  #
# ======================================================================= #
def _candidates(page: dict[str, Any]) -> list[str]:
    return [
        item["text"]
        for bucket in ("links", "buttons", "tabs")
        for item in page.get(bucket, [])
    ]


def _build(page: dict[str, Any], goal: str) -> dict[str, Any]:
    return build_corridor_graph(
        url="https://example.com",
        title="Fixture",
        goal=goal,
        links=page.get("links", []),
        buttons=page.get("buttons", []),
        tabs=page.get("tabs", []),
    ).to_dict()


def full_ranker_pick(payload: dict[str, Any]) -> str | None:
    ch = payload["chosen_corridor"]
    return ch["visible_label"] if ch else None


def _raw_token_overlap(goal: str, edge: dict[str, Any]) -> float:
    goal_tokens = set(goal.lower().split())
    if not goal_tokens:
        return 0.0
    haystack = " ".join(
        [
            str(edge.get("visible_label", "")),
            str(edge.get("role", "")),
            str(edge.get("target_hint", "")),
            str(edge.get("selector", "")),
        ]
    ).lower()
    element_tokens = set(haystack.split())
    return len(goal_tokens & element_tokens) / max(len(goal_tokens), 1)


def plain_overlap_pick(payload: dict[str, Any], goal: str) -> str | None:
    """Discriminating baseline: argmax raw token overlap, independent of router relevance.

    Ties break by DOM order (max returns the first maximizer over edges, which are in DOM
    order) -- a neutral tiebreak, NOT label length (the short-label bias was a v0 confound).
    """
    edges = payload["edges"]
    if not edges:
        return None
    return max(edges, key=lambda e: _raw_token_overlap(goal, e))["visible_label"]


def risk_first_pick(payload: dict[str, Any], dom_order: list[str]) -> str | None:
    by_label = {e["visible_label"]: e for e in payload["edges"]}
    for label in dom_order:
        if label in by_label and by_label[label]["risk_level"] == "low":
            return label
    return dom_order[0] if dom_order else None


def raw_score_argmax_pick(payload: dict[str, Any]) -> str | None:
    """Highest corridor_score ignoring the low-risk hard pre-filter (tests whether the SCORE
    itself is safe, separate from the `next(low-risk)` guarantee)."""
    edges = payload["edges"]
    if not edges:
        return None
    return max(edges, key=lambda e: e["corridor_score"])["visible_label"]


def chosen_risk_level(payload: dict[str, Any]) -> str | None:
    ch = payload["chosen_corridor"]
    return ch["risk_level"] if ch else None


def risk_of(payload: dict[str, Any], label: str | None) -> str | None:
    if label is None:
        return None
    for e in payload["edges"]:
        if e["visible_label"] == label:
            return e["risk_level"]
    return None


# ======================================================================= #
#  Driver                                                                  #
# ======================================================================= #
def build_dataset() -> list[dict[str, Any]]:
    isolation = _audit_heldout_alias_isolation()
    if not isolation["isolated"]:
        raise ValueError(
            "heldout_synonym split is no longer isolated from _SEMANTIC_ALIASES "
            f"(the gate would self-certify): {isolation['violations']}. "
            "Pick fresh held-out synonyms that share no token with the alias vocabulary."
        )
    rng = random.Random(RNG_SEED)
    data = []
    for stratum, gen in STRATA.items():
        for _ in range(SAMPLES_PER_STRATUM):
            page = gen(rng)
            page["stratum"] = stratum
            data.append(page)
    return data


def evaluate(data: list[dict[str, Any]]) -> dict[str, Any]:
    rng = random.Random(RNG_SEED + 1)
    per_stratum: dict[str, Any] = {}
    # cache built payloads under the TRUE goal for reuse in the null
    built: list[tuple[dict[str, Any], dict[str, Any]]] = []

    for stratum in STRATA:
        rows = [p for p in data if p["stratum"] == stratum]
        hits = {"full_ranker": 0, "plain_overlap": 0, "risk_first": 0}
        random_expected = 0.0
        ranker_vs_overlap_disagree = 0
        chosen_highrisk = 0
        rawscore_highrisk = 0
        overlap_highrisk = 0
        n = len(rows)
        for page in rows:
            payload = _build(page, page["goal"])
            built.append((page, payload))
            dom = _candidates(page)
            correct = page["correct"]

            full = full_ranker_pick(payload)
            overlap = plain_overlap_pick(payload, page["goal"])
            rfirst = risk_first_pick(payload, dom)
            raw = raw_score_argmax_pick(payload)

            if full != overlap:
                ranker_vs_overlap_disagree += 1
            if chosen_risk_level(payload) == "high":
                chosen_highrisk += 1
            if risk_of(payload, raw) == "high":
                rawscore_highrisk += 1
            if risk_of(payload, overlap) == "high":
                overlap_highrisk += 1

            if correct is None:
                # success = chose a low-risk corridor (no hallucinated risky routing)
                hits["full_ranker"] += chosen_risk_level(payload) == "low"
                hits["plain_overlap"] += risk_of(payload, overlap) == "low"
                hits["risk_first"] += risk_of(payload, rfirst) == "low"
                random_expected += sum(
                    1 for e in payload["edges"] if e["risk_level"] == "low"
                ) / max(len(payload["edges"]), 1)
            else:
                hits["full_ranker"] += full == correct
                hits["plain_overlap"] += overlap == correct
                hits["risk_first"] += rfirst == correct
                random_expected += 1.0 / max(len(dom), 1)

        per_stratum[stratum] = {
            "n": n,
            "acc_full_ranker": round(hits["full_ranker"] / n, 4),
            "acc_plain_overlap": round(hits["plain_overlap"] / n, 4),
            "acc_risk_first": round(hits["risk_first"] / n, 4),
            "acc_random_expected": round(random_expected / n, 4),
            "full_vs_overlap_disagreement_rate": round(
                ranker_vs_overlap_disagree / n, 4
            ),
            "chosen_highrisk_rate": round(chosen_highrisk / n, 4),
            "rawscore_argmax_highrisk_rate": round(rawscore_highrisk / n, 4),
            "plain_overlap_highrisk_rate": round(overlap_highrisk / n, 4),
        }

    # --- goal-shuffle null: pair each page with another page's goal, keep fixed label ---
    labeled = [(p, pl) for (p, pl) in built if p["correct"] is not None]
    goals = [p["goal"] for (p, _pl) in labeled]
    null_acc = []
    for _ in range(N_NULL):
        shuffled = goals[:]
        rng.shuffle(shuffled)
        hit = 0
        for (page, _orig), g in zip(labeled, shuffled):
            payload = _build(page, g)  # ranker now reads the WRONG goal
            hit += full_ranker_pick(payload) == page["correct"]
        null_acc.append(hit / len(labeled))
    null_mean = sum(null_acc) / len(null_acc)
    null95 = sorted(null_acc)[int(0.95 * (len(null_acc) - 1))]

    true_labeled_acc = sum(
        full_ranker_pick(_build(p, p["goal"])) == p["correct"] for (p, _pl) in labeled
    ) / len(labeled)

    return {
        "per_stratum": per_stratum,
        "goal_shuffle_null": {
            "true_labeled_accuracy": round(true_labeled_acc, 4),
            "null_mean": round(null_mean, 4),
            "null95": round(null95, 4),
            "beats_null": bool(true_labeled_acc > null95),
        },
    }


def _interpret(report: dict[str, Any]) -> str:
    ps = report["per_stratum"]
    low = ps["low_overlap_correct"]
    heldout = ps["heldout_synonym"]
    safety = ps["safety_override"]
    disagree = max(s["full_vs_overlap_disagreement_rate"] for s in ps.values())
    lines = []
    if low["acc_full_ranker"] < 0.6:
        lines.append(
            f"TARGETING IS SHALLOW: on low-overlap-correct the ranker scores "
            f"{low['acc_full_ranker']:.2f} (vs plain-overlap {low['acc_plain_overlap']:.2f}) -- it "
            "matches goal TOKENS, it does not target meaning. A high-overlap distractor beats the "
            "semantically-correct corridor."
        )
    if heldout["acc_full_ranker"] < 0.6:
        lines.append(
            f"HELD-OUT SYNONYMS FAIL: heldout_synonym scores {heldout['acc_full_ranker']:.2f} "
            f"(vs plain-overlap {heldout['acc_plain_overlap']:.2f}); any lexicon scorer must pass "
            "this split without training on these phrases."
        )
    if disagree < 0.05:
        lines.append(
            f"FORMULA REDUCES TO TOKEN-OVERLAP: full ranker disagrees with plain-overlap argmax on "
            f"only {disagree:.0%} of pages -- risk_penalty / selector_confidence / ambiguity / the "
            "prime address are inert for targeting (audit decoration), exactly like phi-weighting in d_H."
        )
    unsafe_baseline = max(
        safety["rawscore_argmax_highrisk_rate"], safety["plain_overlap_highrisk_rate"]
    )
    if safety["chosen_highrisk_rate"] == 0.0 and unsafe_baseline > 0.0:
        lines.append(
            f"SAFETY = HARD FILTER, NOT SCORE: chosen is never high-risk (0%), yet within these same "
            f"pages raw-score argmax routes high-risk {safety['rawscore_argmax_highrisk_rate']:.0%} and "
            f"plain-overlap routes high-risk {safety['plain_overlap_highrisk_rate']:.0%} of the time -- "
            "the realized safety lives entirely in the `next(low-risk)` pre-filter, not in the score."
        )
    gn = report["goal_shuffle_null"]
    lines.append(
        f"GOAL-SHUFFLE NULL: true {gn['true_labeled_accuracy']:.2f} vs null95 {gn['null95']:.2f} -> "
        + (
            "reads the real goal (beats null)"
            if gn["beats_null"]
            else "does NOT beat null"
        )
    )
    return " | ".join(lines)


def main() -> int:
    data = build_dataset()
    report = {
        "harness": "corridor_ranker_baseline",
        "version": "v0-synthetic-controlled-pages",
        "claim_scope": (
            "Artifact-control measurement of the corridor ranking FORMULA against a baseline ladder + "
            "goal-shuffle null, on synthetic pages with overlap-INDEPENDENT ground truth. NOT a real-web "
            "generalization benchmark."
        ),
        "samples_per_stratum": SAMPLES_PER_STRATUM,
        "label_hint_audit": _audit_label_hints(),
        "heldout_alias_isolation": _audit_heldout_alias_isolation(),
        **evaluate(data),
    }
    report["interpretation"] = _interpret(report)

    out = _REPO / "artifacts" / "eval"
    out.mkdir(parents=True, exist_ok=True)
    out_path = out / "corridor_ranker_baseline_v0.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n=== corridor ranker baseline (v0, synthetic controlled pages) ===")
    print(
        "acc = top-1 vs overlap-INDEPENDENT ground truth; hi-risk cols = routed-into-danger rate"
    )
    print(
        f"{'stratum':<22} {'full':>6} {'overlap':>8} {'risk1st':>8} {'rand':>6} "
        f"{'disagr':>7} {'chos.HR':>8} {'raw.HR':>7} {'ovl.HR':>7}"
    )
    for stratum, s in report["per_stratum"].items():
        print(
            f"{stratum:<22} {s['acc_full_ranker']:>6.2f} {s['acc_plain_overlap']:>8.2f} "
            f"{s['acc_risk_first']:>8.2f} {s['acc_random_expected']:>6.2f} "
            f"{s['full_vs_overlap_disagreement_rate']:>7.0%} {s['chosen_highrisk_rate']:>8.0%} "
            f"{s['rawscore_argmax_highrisk_rate']:>7.0%} {s['plain_overlap_highrisk_rate']:>7.0%}"
        )
    gn = report["goal_shuffle_null"]
    print(
        f"\ngoal-shuffle null: true={gn['true_labeled_accuracy']:.2f} "
        f"null95={gn['null95']:.2f} null_mean={gn['null_mean']:.2f} beats_null={gn['beats_null']}"
    )
    print(f"\n-> {report['interpretation']}")
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
