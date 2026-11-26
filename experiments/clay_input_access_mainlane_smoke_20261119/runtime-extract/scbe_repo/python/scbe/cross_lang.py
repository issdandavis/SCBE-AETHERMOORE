"""
Cross-Language Rosetta + cross-compile mini-game
================================================

A lookup table of common coding concepts across languages (a Rosetta row per
concept), plus a tiny game an AI can play to TEST itself at cross-language
"compilation": given a concept in language A, produce it in language B, and the
table grades the answer.

This is the semantic complement to the cube tokenizer: a cube token rotates a
byte across the 6 tongue faces; this table rotates a *coding concept* across
real languages. Same "one idea, many faces" principle, at the source level.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

LANGUAGES = ["python", "javascript", "rust", "go", "ruby", "c"]

# concept -> { language : canonical snippet }
ROSETTA: Dict[str, Dict[str, str]] = {
    "print": {
        "python": 'print("hi")',
        "javascript": 'console.log("hi")',
        "rust": 'println!("hi");',
        "go": 'fmt.Println("hi")',
        "ruby": 'puts "hi"',
        "c": 'printf("hi");',
    },
    "function": {
        "python": "def f(x):",
        "javascript": "function f(x) {}",
        "rust": "fn f(x: i32) {}",
        "go": "func f(x int) {}",
        "ruby": "def f(x)",
        "c": "int f(int x) {}",
    },
    "for_loop": {
        "python": "for i in range(n):",
        "javascript": "for (let i = 0; i < n; i++)",
        "rust": "for i in 0..n {}",
        "go": "for i := 0; i < n; i++ {}",
        "ruby": "n.times do |i|",
        "c": "for (int i = 0; i < n; i++)",
    },
    "if": {
        "python": "if x > 0:",
        "javascript": "if (x > 0) {}",
        "rust": "if x > 0 {}",
        "go": "if x > 0 {}",
        "ruby": "if x > 0",
        "c": "if (x > 0) {}",
    },
    "variable": {
        "python": "x = 5",
        "javascript": "let x = 5;",
        "rust": "let x = 5;",
        "go": "x := 5",
        "ruby": "x = 5",
        "c": "int x = 5;",
    },
    "list": {
        "python": "[1, 2, 3]",
        "javascript": "[1, 2, 3]",
        "rust": "vec![1, 2, 3]",
        "go": "[]int{1, 2, 3}",
        "ruby": "[1, 2, 3]",
        "c": "int a[] = {1, 2, 3};",
    },
    "length": {
        "python": "len(a)",
        "javascript": "a.length",
        "rust": "a.len()",
        "go": "len(a)",
        "ruby": "a.length",
        "c": "sizeof(a)/sizeof(a[0])",
    },
    "comment": {
        "python": "# note",
        "javascript": "// note",
        "rust": "// note",
        "go": "// note",
        "ruby": "# note",
        "c": "/* note */",
    },
    "true": {
        "python": "True",
        "javascript": "true",
        "rust": "true",
        "go": "true",
        "ruby": "true",
        "c": "1",
    },
    "null": {
        "python": "None",
        "javascript": "null",
        "rust": "None",
        "go": "nil",
        "ruby": "nil",
        "c": "NULL",
    },
    "return": {
        "python": "return x",
        "javascript": "return x;",
        "rust": "return x;",
        "go": "return x",
        "ruby": "return x",
        "c": "return x;",
    },
    "while": {
        "python": "while x:",
        "javascript": "while (x) {}",
        "rust": "while x {}",
        "go": "for x {}",
        "ruby": "while x",
        "c": "while (x) {}",
    },
    "class": {
        "python": "class A:",
        "javascript": "class A {}",
        "rust": "struct A {}",
        "go": "type A struct {}",
        "ruby": "class A",
        "c": "struct A {};",
    },
    "import": {
        "python": "import os",
        "javascript": 'import os from "os"',
        "rust": "use std::io;",
        "go": 'import "fmt"',
        "ruby": 'require "set"',
        "c": "#include <stdio.h>",
    },
    "string": {
        "python": '"hi"',
        "javascript": '"hi"',
        "rust": '"hi"',
        "go": '"hi"',
        "ruby": '"hi"',
        "c": '"hi"',
    },
}


def concepts() -> List[str]:
    return list(ROSETTA)


def lookup(concept: str) -> Optional[Dict[str, str]]:
    return ROSETTA.get(concept.strip().lower())


def _normalize(code: str) -> str:
    """Lenient match: ignore whitespace, case, and trailing ; so an AI's answer
    counts if it's the right construct."""
    return "".join(code.split()).rstrip(";").lower()


def grade(concept: str, language: str, answer: str) -> Dict[str, Any]:
    row = lookup(concept)
    if row is None:
        return {"ok": False, "error": f"unknown concept '{concept}'"}
    expected = row.get(language.strip().lower())
    if expected is None:
        return {"ok": False, "error": f"no '{language}' for concept '{concept}'"}
    correct = _normalize(answer) == _normalize(expected)
    return {"ok": True, "correct": correct, "expected": expected, "your_answer": answer}


def challenges(rounds: int = 5, seed: int = 0) -> List[Dict[str, Any]]:
    """Deterministic set of cross-compile challenges (seedable, AI-consumable)."""
    cs = concepts()
    out: List[Dict[str, Any]] = []
    for r in range(rounds):
        s = (seed * 2_654_435_761 + r * 40_503) & 0xFFFFFFFF
        concept = cs[s % len(cs)]
        frm = LANGUAGES[(s >> 4) % len(LANGUAGES)]
        to = LANGUAGES[(s >> 12) % len(LANGUAGES)]
        if to == frm:
            to = LANGUAGES[(LANGUAGES.index(frm) + 1) % len(LANGUAGES)]
        out.append(
            {
                "round": r + 1,
                "concept": concept,
                "from_lang": frm,
                "from_code": ROSETTA[concept][frm],
                "to_lang": to,
                "task": f"write the '{concept}' construct in {to}",
            }
        )
    return out


def _demo() -> None:
    print("Cross-Language Rosetta + cross-compile game\n")
    print(f"concepts: {', '.join(concepts())}")
    print(f"languages: {', '.join(LANGUAGES)}\n")
    print("lookup('print'):")
    for lang, code in lookup("print").items():
        print(f"   {lang:<11} {code}")
    print("\nmini-game challenges (seed=7):")
    for ch in challenges(rounds=3, seed=7):
        print(f"   [{ch['round']}] {ch['from_lang']}: {ch['from_code']:<22} -> {ch['to_lang']}?")
    print("\ngrade an answer:")
    sample_answer = 'println!("hi")'
    print(f"   {grade('print', 'rust', sample_answer)}")


if __name__ == "__main__":
    _demo()
