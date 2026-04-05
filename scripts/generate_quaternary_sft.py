#!/usr/bin/env python3
"""
Generate 500 quaternary L0 substrate SFT pairs.

7 invariants x ~72 pairs each, rotating across 6 tongues and 6 languages.
Deterministic (seeded), schema-compatible with existing L0 SFT files.
"""

import json
import random
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "training-data" / "sft" / "l0_quaternary_substrate_sft.jsonl"

TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]
LANGUAGES = ["Python", "TypeScript", "JavaScript", "Rust", "Go", "C++"]

# The 7 universal quaternary invariants
INVARIANTS = [
    {
        "name": "Nesting Quad",
        "pattern": [1, 3, 0, 2],
        "states": "Open-Balanced-Close-Escaped",
        "description": "Every nesting structure (parentheses, brackets, braces, quotes) follows a 4-state cycle: open (presence), balanced (synthesis), close (null), escaped (opposition).",
        "code_examples": {
            "Python": "def func(a, b):\n    return (a + b) * [c for c in range(10)]",
            "TypeScript": "function parse(input: string): Result<T> {\n  return { ok: true, value: input as T };\n}",
            "JavaScript": "const nested = arr.map((x) => ({ key: x, val: obj[x] ?? null }));",
            "Rust": "fn parse(input: &str) -> Result<Vec<Token>, Error> {\n    input.chars().collect()\n}",
            "Go": "func parse(input string) ([]Token, error) {\n    return tokens, nil\n}",
            "C++": "template<typename T>\nstd::vector<T> parse(const std::string& input) {\n    return {};\n}",
        },
    },
    {
        "name": "Operator Quad",
        "pattern": [1, 2, 3, 0],
        "states": "Action-Comparison-Assignment-Logical",
        "description": "Operators decompose into 4 roles: action (+, -, *, /), comparison (==, <, >), assignment (=, +=), logical (&&, ||, !). Every language has all four.",
        "code_examples": {
            "Python": "result = (a + b) if x > threshold else (a - b)\nvalid = result > 0 and not overflow",
            "TypeScript": "const score: number = (hits / total) >= 0.8 ? bonus + base : base;\nconst valid = score > 0 && !isNaN(score);",
            "JavaScript": "let delta = Math.abs(a - b);\nif (delta <= epsilon || forceAccept) result = a + b;",
            "Rust": "let score = if hits as f64 / total as f64 >= 0.8 { bonus + base } else { base };\nlet valid = score > 0 && !overflow;",
            "Go": "score := hits / total\nif score >= 0.8 && !overflow {\n    result = bonus + base\n}",
            "C++": "double score = static_cast<double>(hits) / total;\nbool valid = (score >= 0.8) && !overflow;",
        },
    },
    {
        "name": "Identifier Quad",
        "pattern": [1, 3, 2, 0],
        "states": "Start-Continue-Digit-Special",
        "description": "Names follow 4 rules: must start with letter/underscore (presence), can continue with alphanumeric (synthesis), digits are positional (opposition), special chars ($, @) are language-specific (null in most).",
        "code_examples": {
            "Python": "_private_var = 42\nMyClass2.__init__(self)\n__dunder__ = True",
            "TypeScript": "const $element: HTMLElement = document.querySelector('#app');\nlet _count2: number = 0;",
            "JavaScript": "const $ref = useRef(null);\nlet _counter2 = 0;\nclass MyComponent3 {}",
            "Rust": "let _unused: i32 = 0;\nstruct MyStruct2 { field_1: String }",
            "Go": "var _counter2 int = 0\ntype MyStruct3 struct { Field1 string }",
            "C++": "int _count2 = 0;\nclass MyClass3 { int m_field1; };",
        },
    },
    {
        "name": "Whitespace Quad",
        "pattern": [0, 1, 2, 3],
        "states": "Space-Tab-Newline-Control",
        "description": "Whitespace has 4 structural roles: space (token separation), tab/indent (scope nesting), newline (statement boundary), control chars (mode switches like \\r, \\0).",
        "code_examples": {
            "Python": "def outer():\n    def inner():\n        return 42\n    return inner()",
            "TypeScript": "function outer(): number {\n  function inner(): number {\n    return 42;\n  }\n  return inner();\n}",
            "JavaScript": "function outer() {\n  const inner = () => {\n    return 42;\n  };\n  return inner();\n}",
            "Rust": "fn outer() -> i32 {\n    fn inner() -> i32 {\n        42\n    }\n    inner()\n}",
            "Go": "func outer() int {\n\tinner := func() int {\n\t\treturn 42\n\t}\n\treturn inner()\n}",
            "C++": "int outer() {\n    auto inner = []() -> int {\n        return 42;\n    };\n    return inner();\n}",
        },
    },
    {
        "name": "Number Quad",
        "pattern": [1, 3, 2, 0],
        "states": "Integer-Float-Scientific-Null",
        "description": "Numeric literals have 4 forms: integer (42), float (3.14), scientific (1e-6), and null/special (NaN, Infinity, None). Every language distinguishes all four at the byte level.",
        "code_examples": {
            "Python": "count = 42\npi = 3.14159\nepsilon = 1e-6\nresult = float('nan') if missing else count",
            "TypeScript": "const count: number = 42;\nconst pi: number = 3.14159;\nconst eps: number = 1e-6;\nconst result: number = isNaN(x) ? 0 : x;",
            "JavaScript": "const count = 42;\nconst pi = 3.14159;\nconst eps = 1e-6;\nconst result = Number.isFinite(x) ? x : 0;",
            "Rust": "let count: i32 = 42;\nlet pi: f64 = 3.14159;\nlet eps: f64 = 1e-6;\nlet result = if x.is_nan() { 0.0 } else { x };",
            "Go": "count := 42\npi := 3.14159\neps := 1e-6\nif math.IsNaN(x) { x = 0.0 }",
            "C++": "int count = 42;\ndouble pi = 3.14159;\ndouble eps = 1e-6;\nif (std::isnan(x)) x = 0.0;",
        },
    },
    {
        "name": "Escape Quad",
        "pattern": [1, 3, 2, 0],
        "states": "Escape-Literal-Command-Synthesis",
        "description": "The escape character (\\) switches interpretation between 4 modes: escape sequence (\\n, \\t), literal string content, command/regex metacharacter, and synthesized output (interpolation, f-strings).",
        "code_examples": {
            "Python": "msg = f\"Hello\\t{name}\\nLine 2\"\npath = r\"C:\\Users\\raw\"  # literal mode\npattern = re.compile(r'\\d+\\.\\d+')",
            "TypeScript": "const msg = `Hello\\t${name}\\nLine 2`;\nconst path = String.raw`C:\\Users\\raw`;\nconst pattern = /\\d+\\.\\d+/;",
            "JavaScript": "const msg = `Hello\\t${name}\\nLine 2`;\nconst escaped = JSON.stringify({key: 'val\\\"ue'});",
            "Rust": "let msg = format!(\"Hello\\t{}\\nLine 2\", name);\nlet path = r\"C:\\Users\\raw\";\nlet pattern = Regex::new(r\"\\d+\\.\\d+\")?;",
            "Go": "msg := fmt.Sprintf(\"Hello\\t%s\\nLine 2\", name)\npath := `C:\\Users\\raw`  // raw literal\npattern := regexp.MustCompile(`\\d+\\.\\d+`)",
            "C++": "std::string msg = \"Hello\\t\" + name + \"\\nLine 2\";\nconst char* path = R\"(C:\\Users\\raw)\";\nstd::regex pattern(R\"(\\d+\\.\\d+)\");",
        },
    },
    {
        "name": "Control Flow Quad",
        "pattern": [1, 2, 3, 0],
        "states": "Enter-Condition-Body-Exit",
        "description": "All control flow follows 4 phases: enter the construct (if/for/try), evaluate condition (test/iteration), execute body (action), exit (else/break/finally). Universal across every language.",
        "code_examples": {
            "Python": "for item in items:\n    if item.valid:\n        process(item)\n    else:\n        skip(item)\n# exit: loop complete",
            "TypeScript": "for (const item of items) {\n  if (item.valid) {\n    process(item);\n  } else {\n    skip(item);\n  }\n}",
            "JavaScript": "try {\n  const result = await fetch(url);\n  if (result.ok) return result.json();\n} catch (e) {\n  handleError(e);\n} finally {\n  cleanup();\n}",
            "Rust": "for item in items.iter() {\n    match item.validate() {\n        Ok(v) => process(v),\n        Err(e) => { log::warn!(\"{e}\"); continue; }\n    }\n}",
            "Go": "for _, item := range items {\n\tif item.Valid {\n\t\tprocess(item)\n\t} else {\n\t\tskip(item)\n\t}\n}",
            "C++": "for (const auto& item : items) {\n    if (item.valid) {\n        process(item);\n    } else {\n        skip(item);\n    }\n}",
        },
    },
]

# Instruction templates for variety — enough to cover 500 unique combos
# With 7 invariants x 6 languages x 12 templates = 504 unique instructions
TEMPLATES = [
    "What is the quaternary quad pattern for {inv_name} in {lang}?",
    "Explain the {inv_name} quaternary invariant ({states}) using {lang} code.",
    "Show the universal quaternary pattern for {states} and how it applies in {lang}.",
    "How does the {inv_name} invariant (quad pattern {pattern}) manifest in {lang} code?",
    "Describe the 4-state {inv_name} pattern as it appears in {lang} programming.",
    "What are the four quaternary states of {inv_name} and how do they appear in {lang}?",
    "Demonstrate the {inv_name} quad invariant ({states}) with a {lang} example.",
    "In {lang}, identify the quaternary {inv_name} cycle ({states}) in this code pattern.",
    "How would you decompose {lang} syntax into the {inv_name} quad ({pattern})?",
    "Analyze the {states} cycle of the {inv_name} invariant — give a {lang} example.",
    "Walk through how {inv_name} maps to 4 structural states in {lang}.",
    "Apply the quaternary substrate analysis ({inv_name}) to typical {lang} constructs.",
]


def build_output(inv: dict, lang: str, tongue: str) -> str:
    """Build a rich but honest output for a quaternary SFT pair."""
    code = inv["code_examples"][lang]
    null_tongues = [t for t in TONGUES if t != tongue][:4]

    return (
        f"The {inv['name']} invariant follows the quaternary pattern {inv['pattern']} "
        f"({inv['states']}).\n\n"
        f"{inv['description']}\n\n"
        f"In {lang}:\n```\n{code}\n```\n\n"
        f"Quaternary state mapping:\n"
        f"- State 0 (null): absence / boundary / inactive\n"
        f"- State 1 (presence): active element / entry point\n"
        f"- State 2 (opposition): complementary / adversarial pair\n"
        f"- State 3 (synthesis): balanced integration of the other three\n\n"
        f"This pattern is universal — it appears identically in every programming language "
        f"because it reflects the structural constraint, not surface syntax. "
        f"The bytes and keywords change per language, but the 4-state cycle is invariant.\n\n"
        f"In the SCBE tongue system, this maps to the {tongue} channel with "
        f"null tongues [{', '.join(null_tongues)}] — the model learns which processing "
        f"channels to skip for this structural pattern."
    )


def main():
    rng = random.Random(42)
    records = []
    seen_instructions = set()

    # Generate unique combos: 7 invariants x 6 languages x 12 templates = 504 possible
    # Use all combos, then trim to 500
    for inv in INVARIANTS:
        for lang in LANGUAGES:
            for t_idx, template in enumerate(TEMPLATES):
                instruction = template.format(
                    inv_name=inv["name"],
                    states=inv["states"],
                    pattern=inv["pattern"],
                    lang=lang,
                )

                # Skip exact duplicates
                if instruction in seen_instructions:
                    continue
                seen_instructions.add(instruction)

                # Rotate tongue based on combo index for even distribution
                combo_idx = len(records)
                tongue = TONGUES[combo_idx % len(TONGUES)]
                null_tongues = [t for t in TONGUES if t != tongue]
                rng.shuffle(null_tongues)

                output = build_output(inv, lang, tongue)

                records.append({
                    "instruction": instruction,
                    "output": output,
                    "layer": "L0",
                    "tongue": tongue,
                    "tongues_active": [tongue],
                    "tongues_null": null_tongues[:4],
                    "category": "quaternary_substrate",
                    "quad_pattern": inv["pattern"],
                    "invariant": inv["name"],
                    "governance": "ALLOW",
                })

    # Shuffle and trim to 500
    rng.shuffle(records)
    records = records[:500]

    # Write
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Stats
    from collections import Counter
    inv_counts = Counter(r["invariant"] for r in records)
    tongue_counts = Counter(r["tongue"] for r in records)
    lang_counts = Counter(r.get("invariant", "") for r in records)

    print(f"Generated {len(records)} quaternary L0 substrate pairs")
    print(f"Output: {OUTPUT}")
    print(f"\nInvariant distribution:")
    for name, count in sorted(inv_counts.items()):
        print(f"  {name}: {count}")
    print(f"\nTongue distribution:")
    for t, count in sorted(tongue_counts.items()):
        print(f"  {t}: {count}")


if __name__ == "__main__":
    main()
