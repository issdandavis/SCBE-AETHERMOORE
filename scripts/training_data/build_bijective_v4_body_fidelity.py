"""Build bijective_v4_body_fidelity SFT dataset.

Target failure modes (from v3 gate, job 69f2dcaa, 64% repaired):
- parse_json_name (extract_name): model omits json.loads call entirely
- bounded_factorial (factorial): UM back-translation drops the n<0 ValueError guard
- eval_runner (run_expr): model fabricates undefined helpers like _ALLOWED

Strategy:
  Train back-translation with contract anchoring (the actual failing step).
  Each pair shape matches the v3 wrapper's build_back_prompt exactly so the model
  learns the response distribution to its inference-time prompts.

Output: training-data/sft/bijective_v4_body_fidelity.sft.jsonl
"""

from __future__ import annotations
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = REPO_ROOT / "training-data" / "sft" / "bijective_v4_body_fidelity.sft.jsonl"

SYSTEM_PROMPT = (
    "You are the SCBE bijective coding agent. The Sacred Tongues map to code languages: "
    "KO=Kor'aelin/Python (phi=1.00), AV=Avali/JavaScript (phi=1.62), "
    "RU=Runethic/Rust (phi=2.62), CA=Cassisivadan/Mathematica (phi=4.24), "
    "UM=Umbroth/Haskell (phi=6.85), DR=Draumric/Markdown (phi=11.09). "
    "Each algorithm decomposes into named SLOTS that hold the same semantic role across "
    "all six tongues. An edit at slot k in any tongue must propagate to slot k in every "
    "other tongue (bijective edit propagation)."
)

TONGUE_LANG = {
    "AV": "JavaScript",
    "RU": "Rust",
    "CA": "Mathematica",
    "UM": "Haskell",
    "DR": "Markdown",
}

# Canonical body-faithful Python for each failing case.
# These satisfy the fixture assertions AND preserve the full body that round-trip drops.
PYTHON_PARSE_JSON = """import json

def extract_name(payload: str):
    try:
        data = json.loads(payload)
    except (ValueError, TypeError):
        return None
    if isinstance(data, dict) and 'name' in data:
        value = data['name']
        if isinstance(value, str):
            return value
    return None"""

PYTHON_FACTORIAL = """def factorial(n: int) -> int:
    if n < 0:
        raise ValueError('factorial requires n >= 0')
    if n == 0:
        return 1
    return n * factorial(n - 1)"""

PYTHON_RUN_EXPR = """def run_expr(expr: str):
    return eval(expr)"""

CANONICAL_PY = {
    "parse_json_name": PYTHON_PARSE_JSON,
    "bounded_factorial": PYTHON_FACTORIAL,
    "eval_runner": PYTHON_RUN_EXPR,
}

# Synthetic intermediate-tongue code. One body-faithful version per (case, tongue).
# These represent what a body-faithful forward translation should look like, so the
# model learns to back-translate them losslessly.
INTERMEDIATES = {
    "parse_json_name": {
        "AV": """function extract_name(payload) {
  let data;
  try {
    data = JSON.parse(payload);
  } catch (e) {
    return null;
  }
  if (data && typeof data === 'object' && 'name' in data) {
    const value = data.name;
    if (typeof value === 'string') {
      return value;
    }
  }
  return null;
}""",
        "RU": """use serde_json::Value;

fn extract_name(payload: &str) -> Option<String> {
    let data: Value = match serde_json::from_str(payload) {
        Ok(v) => v,
        Err(_) => return None,
    };
    match data.get("name") {
        Some(v) => v.as_str().map(|s| s.to_string()),
        None => None,
    }
}""",
        "CA": """ExtractName[payload_String] := Module[{data, value},
  data = Quiet @ Check[ImportString[payload, "JSON"], $Failed];
  If[data === $Failed, Return[Null]];
  If[AssociationQ[data] && KeyExistsQ[data, "name"],
    value = data["name"];
    If[StringQ[value], Return[value]];
  ];
  Null
]""",
        "UM": """import Data.Aeson (decode, Value(..))
import qualified Data.ByteString.Lazy.Char8 as BL
import qualified Data.HashMap.Strict as HM
import Data.Text (unpack)

extract_name :: String -> Maybe String
extract_name payload = do
  Object obj <- decode (BL.pack payload)
  String value <- HM.lookup "name" obj
  return (unpack value)""",
        "DR": """### extract_name(payload)

Parse `payload` as JSON, then return the `name` field if present.

1. Attempt `json.loads(payload)`. On `ValueError` or `TypeError`, return `None`.
2. If the result is a dict and contains the key `'name'`, read its value.
3. If the value is a string, return it.
4. Otherwise return `None`.

Required imports: `import json`.""",
    },
    "bounded_factorial": {
        "AV": """function factorial(n) {
  if (n < 0) {
    throw new Error('factorial requires n >= 0');
  }
  if (n === 0) {
    return 1;
  }
  return n * factorial(n - 1);
}""",
        "RU": """fn factorial(n: i64) -> i64 {
    if n < 0 {
        panic!("factorial requires n >= 0");
    }
    if n == 0 {
        return 1;
    }
    n * factorial(n - 1)
}""",
        "CA": """Factorial[n_Integer] := Module[{},
  If[n < 0, Throw["factorial requires n >= 0"]];
  If[n == 0, Return[1]];
  n * Factorial[n - 1]
]""",
        "UM": """factorial :: Int -> Int
factorial n
  | n < 0     = error "factorial requires n >= 0"
  | n == 0    = 1
  | otherwise = n * factorial (n - 1)""",
        "DR": """### factorial(n)

Compute `n!` recursively.

1. **Guard**: if `n < 0`, raise `ValueError('factorial requires n >= 0')`.
2. **Base case**: if `n == 0`, return `1`.
3. **Recursive case**: return `n * factorial(n - 1)`.

The negative-input guard is mandatory; the function must raise `ValueError` for any
`n < 0` rather than recursing or returning a value.""",
    },
    "eval_runner": {
        "AV": """function run_expr(expr) {
  return eval(expr);
}""",
        "RU": """// Rust has no direct eval; the reference behavior is to forward to a Python
// expression evaluator. The contract is: input string -> evaluated value.
fn run_expr(expr: &str) -> PyObject {
    py_eval(expr)
}""",
        "CA": """RunExpr[expr_String] := ToExpression[expr]""",
        "UM": """-- Haskell has no eval; reference contract: pass the expression string through
-- to the host language's evaluator and return its result.
run_expr :: String -> a
run_expr expr = hostEval expr""",
        "DR": """### run_expr(expr)

Evaluate the Python expression string `expr` using the built-in `eval` function and
return the result.

The function body is one line: `return eval(expr)`. Do **not** add an allow-list, do
**not** validate the expression, do **not** define helper sets like `_ALLOWED`. The
contract is a thin wrapper around `eval` and any added defenses break the bijective
round-trip.""",
    },
}

# Five paraphrases of the back-translation prompt envelope. These mirror the v3
# wrapper's build_back_prompt phrasing while varying surface form.
BACK_PROMPT_TEMPLATES = [
    (
        "Translate the following {lang} function back into idiomatic Python. "
        "Preserve the function's name, parameters, return type, and behavior exactly."
        "{contract}"
        "Output only the Python code inside a single fenced code block. No prose. "
        "Include all required imports inside the code block.\n\n"
        "```{tag}\n{src}\n```\n"
    ),
    (
        "Round-trip this {lang} implementation back to Python. The Python output "
        "MUST keep every guard clause, helper definition, and import that appears in "
        "the canonical contract."
        "{contract}"
        "Reply with only a single fenced ```python``` block.\n\n"
        "```{tag}\n{src}\n```\n"
    ),
    (
        "Back-translate this {lang} code into Python. Preserve full body fidelity: "
        "drop nothing from the canonical contract."
        "{contract}"
        "Output one fenced Python block, no commentary.\n\n"
        "```{tag}\n{src}\n```\n"
    ),
    (
        "Convert this {lang} function back to Python. The result must satisfy the "
        "canonical contract verbatim - same imports, same signature, same guards, "
        "same helpers."
        "{contract}"
        "Respond with only the Python code in a single fenced block.\n\n"
        "```{tag}\n{src}\n```\n"
    ),
    (
        "Render the following {lang} function as Python. Body fidelity is required: "
        "every import, every guard, every helper definition from the contract must "
        "appear in your output."
        "{contract}"
        "One fenced Python block. No prose.\n\n"
        "```{tag}\n{src}\n```\n"
    ),
]

# KO->KO identity (anchor canonical body in Python alone, no round-trip)
KO_IDENTITY_TEMPLATES = [
    "Write a Python function that satisfies this contract:\n\n```\n{contract_text}\n```",
    "Implement the following Python contract. Include all guards and imports.\n\n```\n{contract_text}\n```",
    "Provide the canonical Python implementation for this contract:\n\n```\n{contract_text}\n```",
    "Output the body-faithful Python for this signature contract:\n\n```\n{contract_text}\n```",
    "Render this contract as a complete Python function with full body:\n\n```\n{contract_text}\n```",
]

# Body-fidelity instruction pair (no intermediate; just contract -> python)
CONTRACT_FIDELITY_TEMPLATES = [
    (
        "Given this Python contract, output a body-faithful implementation. Preserve "
        "the {kind_hint} verbatim.\n\n{contract_text}"
    ),
    "Realize the following contract in Python. The {kind_hint} is mandatory.\n\n{contract_text}",
]

CONTRACTS_TEXT = {
    "parse_json_name": (
        "imports: import json\n"
        "signature: def extract_name(payload: str):\n"
        "must call: json.loads on the payload inside a try/except\n"
        "must return: None on parse failure or missing 'name'"
    ),
    "bounded_factorial": (
        "signature: def factorial(n: int) -> int:\n"
        "must raise: ValueError when n < 0\n"
        "base case: n == 0 returns 1\n"
        "recursive case: n * factorial(n - 1)"
    ),
    "eval_runner": (
        "signature: def run_expr(expr: str):\n"
        "body: return eval(expr)\n"
        "constraint: do not add an allow-list, do not define helper sets, "
        "do not validate the expression"
    ),
}

KIND_HINTS = {
    "parse_json_name": "json.loads call inside try/except",
    "bounded_factorial": "n < 0 ValueError guard",
    "eval_runner": "single-line eval forwarding (no allow-list, no helpers)",
}


def extract_contract_block(python_src: str) -> str:
    """Mirror the v3 wrapper's contract-extraction + injection logic."""
    imports: list[str] = []
    signature = ""
    for line in python_src.splitlines():
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            imports.append(stripped)
        elif stripped.startswith("def ") and not signature:
            signature = stripped if stripped.endswith(":") else stripped + ":"
    contract_lines: list[str] = []
    if signature:
        contract_lines.append(f"  Signature (must match exactly): {signature}")
    if imports:
        joined = "\n".join(f"    {i}" for i in imports)
        contract_lines.append(f"  Required imports (must appear at top of code block):\n{joined}")
    if not contract_lines:
        return ""
    return "\nThe Python output MUST satisfy this canonical contract:\n" + "\n".join(contract_lines) + "\n"


def assistant_block(python_src: str) -> str:
    return f"```python\n{python_src}\n```"


def build_pairs() -> list[dict]:
    pairs: list[dict] = []

    for case_id, py_src in CANONICAL_PY.items():
        contract = extract_contract_block(py_src)
        contract_text = CONTRACTS_TEXT[case_id]
        kind_hint = KIND_HINTS[case_id]
        assistant = assistant_block(py_src)

        for tongue, intermediate in INTERMEDIATES[case_id].items():
            lang = TONGUE_LANG[tongue]
            tag = lang.lower()
            for template in BACK_PROMPT_TEMPLATES:
                user_msg = template.format(lang=lang, contract=contract, tag=tag, src=intermediate)
                pairs.append(
                    {
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_msg},
                            {"role": "assistant", "content": assistant},
                        ],
                        "metadata": {
                            "case_id": case_id,
                            "tongue": tongue,
                            "kind": "back_translation_with_contract",
                        },
                    }
                )

        for template in KO_IDENTITY_TEMPLATES:
            user_msg = template.format(contract_text=contract_text)
            pairs.append(
                {
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg},
                        {"role": "assistant", "content": assistant},
                    ],
                    "metadata": {
                        "case_id": case_id,
                        "tongue": "KO",
                        "kind": "ko_identity_anchor",
                    },
                }
            )

        for template in CONTRACT_FIDELITY_TEMPLATES:
            user_msg = template.format(contract_text=contract_text, kind_hint=kind_hint)
            pairs.append(
                {
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg},
                        {"role": "assistant", "content": assistant},
                    ],
                    "metadata": {
                        "case_id": case_id,
                        "tongue": "KO",
                        "kind": "contract_fidelity",
                    },
                }
            )

    return pairs


def main() -> None:
    pairs = build_pairs()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p) + "\n")

    by_case: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    by_tongue: dict[str, int] = {}
    for p in pairs:
        m = p["metadata"]
        by_case[m["case_id"]] = by_case.get(m["case_id"], 0) + 1
        by_kind[m["kind"]] = by_kind.get(m["kind"], 0) + 1
        by_tongue[m["tongue"]] = by_tongue.get(m["tongue"], 0) + 1

    print(f"wrote {len(pairs)} pairs to {OUTPUT_PATH}")
    print("by case:", by_case)
    print("by kind:", by_kind)
    print("by tongue:", by_tongue)


if __name__ == "__main__":
    main()
