"""Natural-language -> reaction-CLI intent parser (deterministic, stdlib-only).

Turns plain requests ("balance propane combustion", "is ethanol controlled?",
"what shape is CO2") into a structured plan that maps onto the existing
``scbe react`` verbs (balance / screen / geometry / checkpoint). It is offline
and dependency-free so it "just works" without an API key -- the same entry
point a human types and an AI agent calls.

Design stance, learned from the lexical shell router that over-fires:
  * STRONG, specific signal  -> a confident plan the caller may execute.
  * WEAK or ambiguous signal -> a low-confidence plan carrying a clarification
    and the exact command it *would* run, so the caller asks instead of guessing.

The parser never fabricates chemistry it cannot resolve; an unknown species
becomes a clarification, not a silent wrong formula.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# --- small, auditable lexicons (common species only; unknowns -> clarify) ---- #

# name -> molecular formula, for the balance lane.
NAME_TO_FORMULA: Dict[str, str] = {
    "water": "H2O",
    "oxygen": "O2",
    "dioxygen": "O2",
    "hydrogen": "H2",
    "nitrogen": "N2",
    "carbon": "C",
    "carbon dioxide": "CO2",
    "carbon monoxide": "CO",
    "methane": "CH4",
    "ethane": "C2H6",
    "propane": "C3H8",
    "butane": "C4H10",
    "octane": "C8H18",
    "ethanol": "C2H6O",
    "methanol": "CH4O",
    "glucose": "C6H12O6",
    "ammonia": "NH3",
    "sodium": "Na",
    "potassium": "K",
    "chlorine": "Cl2",
    "sodium chloride": "NaCl",
    "salt": "NaCl",
    "iron": "Fe",
    "rust": "Fe2O3",
    "iron oxide": "Fe2O3",
    "hydrogen peroxide": "H2O2",
    "sulfuric acid": "H2SO4",
    "hydrochloric acid": "HCl",
    "sodium hydroxide": "NaOH",
    "calcium carbonate": "CaCO3",
    "magnesium": "Mg",
    "magnesium oxide": "MgO",
}

# name -> SMILES, for the screen / geometry lanes (which want a structure).
NAME_TO_SMILES: Dict[str, str] = {
    "water": "O",
    "ethanol": "CCO",
    "methane": "C",
    "ethane": "CC",
    "propane": "CCC",
    "carbon dioxide": "O=C=O",
    "carbon monoxide": "[C-]#[O+]",
    "ammonia": "N",
    "methanol": "CO",
    "benzene": "c1ccccc1",
    "acetone": "CC(C)=O",
    "ethylene": "C=C",
    "acetic acid": "CC(=O)O",
    "aspirin": "CC(=O)OC1=CC=CC=C1C(=O)O",
}

# Verb signals. Order matters: more specific verbs are checked first so a
# generic word ("check") does not steal a clearly geometric/checkpoint request.
_VERB_SIGNALS: List[Tuple[str, List[str]]] = [
    ("checkpoint", ["checkpoint", "merkle", "anchor", "notarize", "seal the chain", "receipt chain"]),
    ("geometry", ["geometry", "shape", "3d", "conformer", "rotor", "point group", "structure of"]),
    ("screen", ["screen", "controlled", "dangerous", "hazardous", "banned", "illegal", "weapon", "schedule"]),
    ("balance", ["balance", "combust", "combustion", "burn", "stoichiometry", "equation", "react"]),
]

_STOPWORDS = {"the", "a", "an", "of", "is", "are", "this", "that", "to", "in", "with", "for", "please", "me", "my"}
# A SMILES token: organic-subset letters/brackets/bonds.
_SMILES_RE = re.compile(r"^[A-Za-z0-9@+\-\[\]()=#$/\\%.]+$")
_FORMULA_RE = re.compile(r"^(?:[A-Z][a-z]?\d*)+(?:\^?\d*[+-])?$")
# Atoms that make up the bulk of an organic SMILES (upper = aliphatic, lower =
# aromatic). Used to accept a bare token like "CCO" as a structure without a
# dictionary, while rejecting English words.
_SMILES_ORGANIC = set("CNOPSFHBIcnopsbi")


@dataclass
class ReactionPlan:
    """A parsed intent ready to map onto a ``scbe react`` builder call."""

    verb: Optional[str]
    args: Dict[str, str] = field(default_factory=dict)
    canonical_command: str = ""
    confidence: float = 0.0
    clarification: Optional[str] = None
    notes: List[str] = field(default_factory=list)

    @property
    def confident(self) -> bool:
        """High enough to act on without asking the user first."""
        return self.verb is not None and self.confidence >= 0.6 and self.clarification is None


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _is_verb_word(token: str) -> bool:
    return any(sig in token.lower() for _, sigs in _VERB_SIGNALS for sig in sigs)


def _candidate_structure_token(token: str) -> bool:
    """True if a bare token is plausibly a SMILES/structure rather than English.

    Accepts tokens with structural punctuation/digits (O=C=O, c1ccccc1) and bare
    organic strings with an uppercase atom (CCO, CC) while rejecting words like
    'stuff' or verb words ('screen', 'geometry')."""
    if not _SMILES_RE.match(token) or token.lower() in _STOPWORDS or _is_verb_word(token):
        return False
    has_structure = any(c in token for c in "=#()[]/\\@+") or any(c.isdigit() for c in token)
    has_upper = any(c.isupper() for c in token)
    organic_frac = sum(c in _SMILES_ORGANIC for c in token) / max(len(token), 1)
    return has_structure or (has_upper and organic_frac >= 0.6)


def _resolve_species_formula(text: str) -> Tuple[List[str], List[str]]:
    """Return (formulas_found, names_unresolved) scanning the text for species."""
    found: List[str] = []
    unresolved: List[str] = []
    lowered = text.lower()
    # multi-word names first (longest match wins), then single tokens / formulas.
    for name in sorted(NAME_TO_FORMULA, key=len, reverse=True):
        if re.search(rf"\b{re.escape(name)}\b", lowered):
            found.append(NAME_TO_FORMULA[name])
            lowered = re.sub(rf"\b{re.escape(name)}\b", " ", lowered)
    for tok in re.findall(r"[A-Za-z0-9]+", text):
        if _FORMULA_RE.match(tok) and tok not in found and any(c.isupper() for c in tok) and len(tok) >= 2:
            # crude: treat capitalized multi-char tokens that are valid formulas
            # as formulas (CO2, H2O, C3H8) but skip words already consumed.
            if tok.lower() not in NAME_TO_FORMULA and re.search(r"\d", tok) or tok in {"O2", "H2", "N2"}:
                found.append(tok)
    return found, unresolved


def _parse_equation(text: str) -> Optional[Tuple[List[str], List[str]]]:
    """If the text contains an explicit A + B -> C + D equation, parse it."""
    arrow = re.search(r"->|→|=>|=", text)
    if not arrow:
        return None
    left, right = text[: arrow.start()], text[arrow.end() :]

    def species(side: str) -> List[str]:
        out: List[str] = []
        for part in re.split(r"\+", side):
            # A part may carry a leading verb word or coefficient ("balance C3H8",
            # "5 O2"); scan it for the formula/name token rather than treating the
            # whole segment as one token.
            matched: Optional[str] = None
            for tok in re.findall(r"[A-Za-z0-9^+\-]+", part):
                if _FORMULA_RE.match(tok) and any(c.isupper() for c in tok):
                    matched = tok
                elif tok.lower() in NAME_TO_FORMULA:
                    matched = NAME_TO_FORMULA[tok.lower()]
            if matched:
                out.append(matched)
        return out

    reactants, products = species(left), species(right)
    if reactants and products:
        return reactants, products
    return None


def _detect_verb(text: str) -> Optional[str]:
    lowered = text.lower()
    for verb, signals in _VERB_SIGNALS:
        if any(sig in lowered for sig in signals):
            return verb
    return None


def _find_smiles_or_named_structure(text: str) -> Tuple[Optional[str], List[str]]:
    """Pull a SMILES (or a known molecule name -> SMILES) for screen/geometry."""
    notes: List[str] = []
    lowered = text.lower()
    for name in sorted(NAME_TO_SMILES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(name)}\b", lowered):
            notes.append(f"resolved '{name}' -> {NAME_TO_SMILES[name]}")
            return NAME_TO_SMILES[name], notes
    # explicit CAS number?
    cas = re.search(r"\b\d{2,7}-\d{2}-\d\b", text)
    if cas:
        return cas.group(0), notes
    # otherwise the longest structure-looking token, skipping stopwords/verbs.
    candidates = [t for t in re.findall(r"\S+", text) if _candidate_structure_token(t)]
    if candidates:
        return max(candidates, key=len), notes
    return None, notes


def _find_path(text: str) -> Optional[str]:
    for tok in re.findall(r"\S+", text):
        if tok.endswith(".json") or "/" in tok or "\\" in tok:
            return tok
    return None


def _plan_balance(text: str) -> ReactionPlan:
    notes: List[str] = []
    eq = _parse_equation(text)
    if eq:
        reactants, products = eq
        cmd = f"react balance --reactants {','.join(reactants)} --products {','.join(products)}"
        return ReactionPlan(
            "balance",
            {"reactants": ",".join(reactants), "products": ",".join(products)},
            cmd,
            0.9,
            notes=["parsed an explicit equation"],
        )
    lowered = text.lower()
    formulas, _ = _resolve_species_formula(text)
    is_combustion = any(w in lowered for w in ("combust", "combustion", "burn"))
    if is_combustion and formulas:
        fuel = next((f for f in formulas if f != "O2"), None)
        if fuel:
            reactants = [fuel, "O2"]
            products = ["CO2", "H2O"]
            cmd = f"react balance --reactants {','.join(reactants)} --products {','.join(products)}"
            return ReactionPlan(
                "balance",
                {"reactants": ",".join(reactants), "products": ",".join(products)},
                cmd,
                0.78,
                notes=[
                    f"combustion template: {fuel} + O2 -> CO2 + H2O",
                    "the balancer verifies conservation; if the fuel has other elements it will say so",
                ],
            )
    if len(formulas) >= 2:
        # Can't tell sides apart without an arrow -> clarify rather than guess.
        cmd = f"react balance --reactants {','.join(formulas[:-1])} --products {formulas[-1]}"
        return ReactionPlan(
            "balance",
            {},
            cmd,
            0.4,
            clarification=(
                f"I found species {formulas} but not which are reactants vs products. "
                f"Give it as an equation, e.g. '{' + '.join(formulas[:-1])} -> {formulas[-1]}'."
            ),
            notes=notes,
        )
    return ReactionPlan(
        "balance",
        {},
        "react balance --reactants <A,B> --products <C,D>",
        0.25,
        clarification="Tell me the reaction as an equation, e.g. 'balance C3H8 + O2 -> CO2 + H2O'.",
    )


def _plan_screen(text: str) -> ReactionPlan:
    smiles, notes = _find_smiles_or_named_structure(text)
    if smiles:
        return ReactionPlan(
            "screen",
            {"input": smiles},
            f"react screen --input {smiles}",
            0.85,
            notes=notes,
        )
    return ReactionPlan(
        "screen",
        {},
        "react screen --input <SMILES|CAS>",
        0.3,
        clarification="What should I screen? Give a SMILES (e.g. CCO) or a CAS number.",
    )


def _plan_geometry(text: str) -> ReactionPlan:
    smiles, notes = _find_smiles_or_named_structure(text)
    if smiles and not re.match(r"^\d", smiles):  # geometry needs a SMILES, not a CAS
        return ReactionPlan(
            "geometry",
            {"smiles": smiles},
            f"react geometry --smiles {smiles}",
            0.85,
            notes=notes,
        )
    return ReactionPlan(
        "geometry",
        {},
        "react geometry --smiles <SMILES>",
        0.3,
        clarification="Which molecule? Give a SMILES (e.g. CCO for ethanol) or a name I know.",
    )


def _plan_checkpoint(text: str) -> ReactionPlan:
    path = _find_path(text)
    if path:
        return ReactionPlan(
            "checkpoint",
            {"packets": path},
            f"react checkpoint --packets {path}",
            0.85,
            notes=["add --rekor-dry-run for an anchor-ready (offline) digest"],
        )
    return ReactionPlan(
        "checkpoint",
        {},
        "react checkpoint --packets <file.json>",
        0.3,
        clarification="Which packet/chain file should I checkpoint? Give a path to a .json file.",
    )


_DISPATCH = {
    "balance": _plan_balance,
    "screen": _plan_screen,
    "geometry": _plan_geometry,
    "checkpoint": _plan_checkpoint,
}

VERBS_HELP = (
    "I understand these reaction requests:\n"
    "  balance    e.g. 'balance propane combustion' / 'balance C3H8 + O2 -> CO2 + H2O'\n"
    "  screen     e.g. 'is ethanol controlled?' / 'screen CCO'\n"
    "  geometry   e.g. 'what shape is CO2?' / 'geometry of ethanol'\n"
    "  checkpoint e.g. 'checkpoint artifacts/demo/methalox/signed_chain.json'"
)


def plan_from_text(text: str) -> ReactionPlan:
    """Parse free text into a ReactionPlan mapped onto a ``scbe react`` verb."""
    text = _normalize(text)
    if not text:
        return ReactionPlan(None, {}, "", 0.0, clarification="Say what you want, e.g. 'balance methane combustion'.")
    lowered = text.lower()
    if lowered in {"help", "?", "what can you do", "commands"} or lowered.startswith("help"):
        return ReactionPlan("help", {}, "react ask --help", 1.0, notes=[VERBS_HELP])

    verb = _detect_verb(text)
    # An explicit equation implies balance even without a verb word.
    if verb is None and _parse_equation(text):
        verb = "balance"
    if verb is None:
        # No verb signal: offer the menu rather than guess.
        return ReactionPlan(
            None,
            {},
            "",
            0.2,
            clarification="I couldn't tell which reaction operation you meant.\n" + VERBS_HELP,
        )
    return _DISPATCH[verb](text)
