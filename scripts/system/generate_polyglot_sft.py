"""
Generate polyglot cross-language SFT training data using the ca_lexicon as the swap table.

Each tongue maps to a canonical programming language (from ca_lexicon/__init__.py):
    KO (Kor'aelin)    -> Python
    AV (Avali)        -> TypeScript
    RU (Runethic)     -> Rust
    CA (Cassisivadan) -> C
    UM (Umbroth)      -> Julia
    DR (Draumric)     -> Haskell
    GO (extended)     -> Go
    ZI (extended)     -> Zig

Training record types:
    TYPE-N: Native   -- code in tongue X's language, high X tongue weight
    TYPE-S: Swap     -- the ca_lexicon swap guide for X->Y, equal X/Y weights (Mobius transition at L7)
    TYPE-T: Translate-- given code in X + swap guide, produce Y; weights shift X->Y
    TYPE-X: Cross    -- same algorithm in all 6 languages, shows pattern invariance

The swap guide IS the ca_lexicon. The command swap IS the Mobius rotation in tongue space.
L7 (Mobius phase) is the active layer during any tongue transition.

Usage:
    python scripts/system/generate_polyglot_sft.py
    python scripts/system/generate_polyglot_sft.py --pairs KO-AV KO-RU AV-RU
    python scripts/system/generate_polyglot_sft.py --all-pairs
    python scripts/system/generate_polyglot_sft.py --dry-run
"""

import argparse
import hashlib
import json
import random
from pathlib import Path

# ---------------------------------------------------------------------------
# Canonical tongue->language mapping (from ca_lexicon)
# ---------------------------------------------------------------------------

LANG_MAP = {
    "KO": "Python",
    "AV": "TypeScript",
    "RU": "Rust",
    "CA": "C",
    "UM": "Julia",
    "DR": "Haskell",
    "GO": "Go",
    "ZI": "Zig",
}

TONGUE_FULL = {
    "KO": "Kor'aelin",
    "AV": "Avali",
    "RU": "Runethic",
    "CA": "Cassisivadan",
    "UM": "Umbroth",
    "DR": "Draumric",
    "GO": "Go-Tongue",
    "ZI": "Zig-Tongue",
}

# Tongue weights: native tongue gets 0.70, others share remaining 0.30
def native_weights(tongue: str) -> dict:
    base = {t: round(0.30 / 5, 3) for t in ["KO", "AV", "RU", "CA", "UM", "DR"]}
    base[tongue] = 0.700
    return base

def transition_weights(src: str, dst: str) -> dict:
    base = {t: round(0.10 / 4, 3) for t in ["KO", "AV", "RU", "CA", "UM", "DR"] if t not in (src, dst)}
    base[src] = 0.420
    base[dst] = 0.420
    # Mobius transition: equal source/dest, others squeezed
    total = sum(base.values())
    # Normalize
    factor = 1.0 / total
    return {k: round(v * factor, 3) for k, v in base.items()}

def result_weights(dst: str) -> dict:
    return native_weights(dst)

# ---------------------------------------------------------------------------
# Command swap tables: (source_tongue, dest_tongue) -> list of swap rules
# Each rule: {"from": pattern, "to": pattern, "why": explanation}
# ---------------------------------------------------------------------------

SWAP_TABLES = {
    ("KO", "AV"): {  # Python -> TypeScript
        "syntax": [
            {"from": "def {name}({args}):",        "to": "function {name}({args}): {ret} {",    "why": "Python uses 'def', TS uses 'function'; block opened with {"},
            {"from": "    return {x}",              "to": "    return {x};\n}",                  "why": "TS requires semicolons; closing brace closes the function"},
            {"from": "print({x})",                  "to": "console.log({x})",                    "why": "Python's built-in print -> browser/Node console.log"},
            {"from": 'f"{x}"',                      "to": "`${x}`",                              "why": "f-string interpolation -> template literal backtick syntax"},
            {"from": "if {cond}:",                  "to": "if ({cond}) {",                       "why": "TS wraps condition in parens, opens block with {"},
            {"from": "for {i} in range({n}):",      "to": "for (let {i} = 0; {i} < {n}; {i}++) {", "why": "Python range loop -> C-style for loop in TS"},
            {"from": "for {item} in {lst}:",        "to": "for (const {item} of {lst}) {",       "why": "Python for-in -> TS for-of (for-in iterates keys)"},
            {"from": "while {cond}:",               "to": "while ({cond}) {",                    "why": "Same logic, TS adds parens and brace"},
            {"from": "elif {cond}:",                "to": "} else if ({cond}) {",                "why": "Python elif -> TS else if with brace close/open"},
            {"from": "else:",                       "to": "} else {",                            "why": "Python else -> TS else with brace"},
            {"from": "try:",                        "to": "try {",                               "why": "Exception block opening"},
            {"from": "except {E} as {e}:",          "to": "} catch ({e}: {E}) {",               "why": "Python except -> TS catch; type annotation inline"},
            {"from": "finally:",                    "to": "} finally {",                         "why": "Finally block syntax"},
            {"from": "class {Name}:",               "to": "class {Name} {",                      "why": "Class definition; TS opens with brace"},
            {"from": "    def __init__(self, {a}):", "to": "    constructor({a}) {",             "why": "__init__ -> constructor in TypeScript"},
            {"from": "    def {m}(self, {a}):",     "to": "    {m}({a}): {ret} {",              "why": "Instance method: drop self, add return type"},
            {"from": "import {mod}",                "to": "import * as {mod} from '{mod}'",      "why": "Python import -> ES module import"},
            {"from": "from {mod} import {x}",       "to": "import { {x} } from '{mod}'",        "why": "Named import syntax"},
            {"from": "# {comment}",                 "to": "// {comment}",                        "why": "Hash comments -> C-style double-slash"},
            {"from": "\"\"\"...\"\"\"",             "to": "/** ... */",                          "why": "Docstring -> JSDoc"},
        ],
        "types": [
            {"from": ": int",    "to": ": number",              "why": "Python int -> TS number (no integer/float split)"},
            {"from": ": float",  "to": ": number",              "why": "Python float -> TS number"},
            {"from": ": str",    "to": ": string",              "why": "Python str -> TS string"},
            {"from": ": bool",   "to": ": boolean",             "why": "Python bool -> TS boolean"},
            {"from": ": list",   "to": ": Array<any>",          "why": "Python list -> TS Array; specify element type"},
            {"from": ": dict",   "to": ": Record<string, any>", "why": "Python dict -> TS Record"},
            {"from": "None",     "to": "null",                  "why": "Python None -> JS null"},
            {"from": "True",     "to": "true",                  "why": "Python True -> JS true (lowercase)"},
            {"from": "False",    "to": "false",                 "why": "Python False -> JS false (lowercase)"},
            {"from": "Optional[{T}]", "to": "{T} | null",       "why": "Optional -> union with null"},
        ],
        "naming": [
            {"from": "snake_case",  "to": "camelCase",           "why": "Python convention is snake_case; TS/JS uses camelCase for variables/functions"},
            {"from": "SCREAMING",   "to": "SCREAMING",           "why": "Constants keep SCREAMING_SNAKE in both"},
            {"from": "PascalCase",  "to": "PascalCase",          "why": "Classes stay PascalCase in both"},
        ],
        "l7_note": "Kor'aelin->Avali rotation: flow/intent (KO) expands to typed context/I/O (AV). Weights shift from KO=0.70 through the Mobius midpoint KO=AV=0.42 to AV=0.70.",
    },
    ("KO", "RU"): {  # Python -> Rust
        "syntax": [
            {"from": "def {name}({args}) -> {ret}:", "to": "fn {name}({args}) -> {ret} {",      "why": "def -> fn; return type uses ->; block opens with {"},
            {"from": "    return {x}",               "to": "    {x}",                            "why": "Rust uses implicit returns (no return keyword for last expression)"},
            {"from": "print({x})",                   "to": 'println!("{}", {x})',                "why": "print -> println! macro; format string required"},
            {"from": "{x} = {val}",                  "to": "let {x} = {val};",                  "why": "Python assignment -> Rust let binding with semicolon"},
            {"from": "{x}: int = {val}",             "to": "let {x}: i32 = {val};",             "why": "Python int -> Rust i32 (default integer type)"},
            {"from": "{x}: float = {val}",           "to": "let {x}: f64 = {val};",             "why": "Python float -> Rust f64"},
            {"from": "{x}: str = {val}",             "to": 'let {x}: &str = {val};',            "why": "Python str -> Rust &str (borrowed string slice)"},
            {"from": "if {cond}:",                   "to": "if {cond} {",                        "why": "No parens needed in Rust; block opens with {"},
            {"from": "else:",                        "to": "} else {",                           "why": "Else block"},
            {"from": "for {i} in range({n}):",       "to": "for {i} in 0..{n} {",              "why": "Python range -> Rust range literal 0..n"},
            {"from": "for {item} in {lst}:",         "to": "for {item} in &{lst} {",            "why": "Rust borrows the collection; & prevents move"},
            {"from": "try: ... except {E}:",         "to": "match {expr} { Ok(v) => v, Err(e) => ... }", "why": "Python exceptions -> Rust Result<T,E> with match"},
            {"from": "class {Name}:",                "to": "struct {Name} {",                   "why": "Python class -> Rust struct (methods go in impl block)"},
            {"from": "    def {m}(self, {a}):",      "to": "impl {Name} {\n    fn {m}(&self, {a}) {", "why": "Methods in impl block; &self = borrowed self"},
            {"from": "import {mod}",                 "to": "use {mod};",                        "why": "Python import -> Rust use"},
            {"from": "# {comment}",                  "to": "// {comment}",                      "why": "Hash -> double-slash comment"},
            {"from": "None",                         "to": "None",                              "why": "Same keyword, but in Option<T> context"},
        ],
        "types": [
            {"from": "int",      "to": "i32",                   "why": "Default Python int -> Rust 32-bit signed integer"},
            {"from": "float",    "to": "f64",                   "why": "Python float -> Rust 64-bit float"},
            {"from": "str",      "to": "&str",                  "why": "Borrowed string; use String for owned strings"},
            {"from": "bool",     "to": "bool",                  "why": "Same type name"},
            {"from": "list[T]",  "to": "Vec<T>",                "why": "Python list -> Rust Vec (heap-allocated growable array)"},
            {"from": "dict[K,V]","to": "HashMap<K, V>",         "why": "Python dict -> Rust HashMap (must import std::collections::HashMap)"},
            {"from": "Optional[T]", "to": "Option<T>",          "why": "Optional value -> Rust Option enum (Some(T) or None)"},
            {"from": "Exception", "to": "Box<dyn Error>",       "why": "Rust errors are trait objects or custom enum variants"},
            {"from": "True/False","to": "true/false",           "why": "Lowercase in Rust"},
        ],
        "ownership": [
            {"from": "pass by ref (default)", "to": "& (borrow)",     "why": "Rust makes memory ownership explicit. & borrows without moving."},
            {"from": "pass by value",         "to": "value (move)",   "why": "Passing without & transfers ownership; original variable becomes invalid."},
            {"from": "mutable var",           "to": "let mut {x}",    "why": "Variables are immutable by default in Rust; add mut to allow mutation."},
        ],
        "l7_note": "Kor'aelin->Runethic rotation: intent/flow (KO) becomes binding/ownership/policy (RU). Every variable binding is a policy contract in Rust.",
    },
    ("KO", "CA"): {  # Python -> C
        "syntax": [
            {"from": "def {name}({args}) -> {ret}:", "to": "{ret} {name}({args}) {",            "why": "C puts return type first; no 'def' keyword"},
            {"from": "    return {x}",               "to": "    return {x};",                   "why": "C requires semicolons everywhere"},
            {"from": "print({x})",                   "to": 'printf("%s\\n", {x})',              "why": "C printf with format string; %d for int, %f for float, %s for string"},
            {"from": "{x} = {val}",                  "to": "{type} {x} = {val};",              "why": "C requires explicit type declaration"},
            {"from": "if {cond}:",                   "to": "if ({cond}) {",                     "why": "C wraps condition in parens"},
            {"from": "else:",                        "to": "} else {",                          "why": "Else block"},
            {"from": "for {i} in range({n}):",       "to": "for (int {i} = 0; {i} < {n}; {i}++) {", "why": "C for loop: init; condition; increment"},
            {"from": "while {cond}:",                "to": "while ({cond}) {",                  "why": "Same logic, C adds parens"},
            {"from": "import {mod}",                 "to": "#include <{mod}.h>",               "why": "C uses preprocessor includes, not imports"},
            {"from": "class {Name}:",                "to": "typedef struct {Name} {",           "why": "C structs + typedef for class-like behavior"},
            {"from": "# {comment}",                  "to": "// {comment}",                      "why": "Hash -> double-slash (C99+)"},
            {"from": "\"\"\"...\"\"\"",              "to": "/* ... */",                         "why": "Docstring -> C block comment"},
            {"from": "None",                         "to": "NULL",                              "why": "Python None -> C NULL pointer"},
            {"from": "True/False",                   "to": "1/0",                               "why": "C has no bool by default; use int or #include <stdbool.h>"},
        ],
        "types": [
            {"from": "int",     "to": "int",                    "why": "Same name; but C int is platform-dependent size"},
            {"from": "float",   "to": "double",                 "why": "Python float is 64-bit; C double matches"},
            {"from": "str",     "to": "char*",                  "why": "Python strings -> C char pointer (null-terminated)"},
            {"from": "bool",    "to": "int (or _Bool)",         "why": "No native bool in C89; use #include <stdbool.h> for bool"},
            {"from": "list",    "to": "{type}[] or {type}*",    "why": "C arrays are fixed-size; dynamic arrays need malloc"},
            {"from": "dict",    "to": "struct / hash table",    "why": "No built-in dict; implement as struct or use a hash table library"},
        ],
        "memory": [
            {"from": "automatic (GC)",     "to": "manual (malloc/free)",  "why": "Python manages memory automatically; C requires you to allocate and free heap memory manually"},
            {"from": "list.append(x)",     "to": "arr[i++] = x",          "why": "No dynamic append; you manage the index and size yourself"},
            {"from": "del x",              "to": "free(x)",               "why": "Python del -> C free() for heap memory; stack memory frees automatically"},
        ],
        "l7_note": "Kor'aelin->Cassisivadan rotation: intent/flow (KO) becomes raw compute/ciphertext (CA). C exposes the machine directly — no abstraction layer between code and hardware.",
    },
    ("KO", "UM"): {  # Python -> Julia
        "syntax": [
            {"from": "def {name}({args}):",         "to": "function {name}({args})",           "why": "Python def -> Julia function; no colon, ends with 'end'"},
            {"from": "    return {x}",              "to": "    return {x}\nend",               "why": "Julia blocks close with 'end' keyword"},
            {"from": "print({x})",                  "to": "println({x})",                      "why": "Python print -> Julia println (no parens required but accepted)"},
            {"from": "{x} = {val}",                 "to": "{x} = {val}",                      "why": "Assignment is identical; Julia is dynamically typed by default"},
            {"from": "if {cond}:",                  "to": "if {cond}",                         "why": "No colon; block ends with 'end'"},
            {"from": "else:",                       "to": "else",                              "why": "Else keyword, no colon"},
            {"from": "elseif ... :",                "to": "elseif ...",                        "why": "Julia uses elseif (one word), no colon"},
            {"from": "for {i} in range({n}):",      "to": "for {i} in 1:{n}",                "why": "Julia ranges are 1-indexed! 1:n is inclusive"},
            {"from": "for {item} in {lst}:",        "to": "for {item} in {lst}",              "why": "Same logic, no colon"},
            {"from": "while {cond}:",               "to": "while {cond}",                     "why": "While loop, ends with 'end'"},
            {"from": "try: ... except {E}:",        "to": "try\n    ...\ncatch {e}::{E}",    "why": "Julia try/catch with :: type assertion"},
            {"from": "class {Name}:",               "to": "struct {Name}",                    "why": "Immutable struct by default; use 'mutable struct' for mutation"},
            {"from": "import {mod}",                "to": "using {mod}",                      "why": "Python import -> Julia using"},
            {"from": "from {mod} import {x}",       "to": "using {mod}: {x}",                "why": "Named import from module"},
            {"from": "# {comment}",                 "to": "# {comment}",                     "why": "Same hash comment syntax"},
            {"from": "None",                        "to": "nothing",                          "why": "Python None -> Julia nothing"},
            {"from": "True/False",                  "to": "true/false",                       "why": "Lowercase in Julia"},
        ],
        "types": [
            {"from": "int",     "to": "Int64",                  "why": "Julia defaults to 64-bit integers"},
            {"from": "float",   "to": "Float64",                "why": "Julia defaults to 64-bit floats"},
            {"from": "str",     "to": "String",                 "why": "String type (capitalized)"},
            {"from": "bool",    "to": "Bool",                   "why": "Bool type (capitalized)"},
            {"from": "list",    "to": "Vector{T}",              "why": "Julia Vector is typed; Vector{Any} for mixed"},
            {"from": "dict",    "to": "Dict{K, V}",             "why": "Julia Dict with explicit key/value types"},
            {"from": "Optional[T]", "to": "Union{T, Nothing}", "why": "Julia uses type unions for optional values"},
        ],
        "l7_note": "Kor'aelin->Umbroth rotation: Python flow (KO) becomes Julia's numerical/scientific compute (UM). Julia reads like Python but executes at C speed — the redaction layer hides the compilation overhead.",
    },
    ("KO", "DR"): {  # Python -> Haskell
        "syntax": [
            {"from": "def {name}({args}):",         "to": "{name} :: {arg_types} -> {ret}\n{name} {args} =", "why": "Haskell: type signature on its own line, then definition"},
            {"from": "    return {x}",              "to": "    {x}",                           "why": "Haskell is expression-based; last expression IS the return value"},
            {"from": "print({x})",                  "to": "putStrLn {x}",                     "why": "Haskell IO action; putStr without newline, putStrLn with"},
            {"from": "{x} = {val}",                 "to": "let {x} = {val}",                 "why": "let binding in do-notation or where clause"},
            {"from": "if {cond}:",                  "to": "if {cond}",                        "why": "Haskell if is an expression: if cond then x else y"},
            {"from": "else:",                       "to": "else",                             "why": "else is mandatory in Haskell (if is an expression, must return a value)"},
            {"from": "for {i} in range({n}):",      "to": "mapM_ (\\{i} -> ...) [0..{n}-1]", "why": "No for loops; use map/mapM_ or list comprehensions"},
            {"from": "for {item} in {lst}:",        "to": "mapM_ (\\{item} -> ...) {lst}",   "why": "Haskell iterates by applying a function to each element"},
            {"from": "while {cond}: ...",           "to": "until (not . {cond}) (\\s -> ...)", "why": "No while; use recursion or higher-order functions"},
            {"from": "try: ... except {E}:",        "to": "catch (\\e -> ...) action",        "why": "Haskell uses Control.Exception.catch or Either monad"},
            {"from": "class {Name}:",               "to": "data {Name} = {Name} { ... }",    "why": "Haskell data types with record syntax; typeclass for methods"},
            {"from": "import {mod}",                "to": "import {Mod}",                    "why": "Haskell module names are capitalized"},
            {"from": "# {comment}",                 "to": "-- {comment}",                    "why": "Haskell uses double-dash for line comments"},
            {"from": "None",                        "to": "Nothing",                         "why": "Haskell Maybe monad: Nothing or Just x"},
            {"from": "Optional[T]",                 "to": "Maybe {T}",                       "why": "Optional -> Haskell's Maybe monad"},
        ],
        "types": [
            {"from": "int",     "to": "Int",                    "why": "Fixed-size integer; Integer for arbitrary precision"},
            {"from": "float",   "to": "Double",                 "why": "Haskell Double = 64-bit float"},
            {"from": "str",     "to": "String",                 "why": "String = [Char] in Haskell (list of characters)"},
            {"from": "bool",    "to": "Bool",                   "why": "Bool with capital B"},
            {"from": "list[T]", "to": "[T]",                    "why": "Haskell list syntax is brackets: [Int], [String]"},
            {"from": "dict",    "to": "Map.Map k v",            "why": "Data.Map.Map from containers library"},
        ],
        "l7_note": "Kor'aelin->Draumric rotation: imperative flow (KO) becomes pure functional schema (DR). Haskell enforces referential transparency — a function's output depends ONLY on its inputs, like a mathematical proof.",
    },
    ("AV", "RU"): {  # TypeScript -> Rust
        "syntax": [
            {"from": "function {name}({args}): {ret} {", "to": "fn {name}({args}) -> {ret} {", "why": "TS function -> Rust fn; return type moves to after ->"},
            {"from": "const {x} = {val};",           "to": "let {x} = {val};",               "why": "TS const -> Rust let (immutable by default)"},
            {"from": "let {x} = {val};",             "to": "let mut {x} = {val};",           "why": "TS mutable let -> Rust let mut (explicit mutability)"},
            {"from": "console.log({x})",             "to": 'println!("{:?}", {x})',           "why": "console.log -> Rust println! macro with debug format"},
            {"from": "throw new Error({msg})",       "to": "return Err({msg}.into())",        "why": "Exceptions -> Result type; return Err to propagate"},
            {"from": "try { ... } catch(e) { ... }", "to": "match {expr} { Ok(v) => v, Err(e) => ... }", "why": "try/catch -> Rust match on Result"},
            {"from": "interface {Name} { ... }",     "to": "trait {Name} { ... }",            "why": "TS interface -> Rust trait (for shared behavior)"},
            {"from": "type {Name} = { ... }",        "to": "struct {Name} { ... }",           "why": "TS type alias with shape -> Rust struct"},
            {"from": "Promise<{T}>",                 "to": "Future<Output = {T}>",            "why": "TS Promise -> Rust Future (async/await works in both)"},
            {"from": "async function {name}(...):",  "to": "async fn {name}(...) -> {ret} {", "why": "Async syntax is similar; Rust requires .await explicitly"},
            {"from": "import { {x} } from '{mod}'",  "to": "use {mod}::{x};",               "why": "ES import -> Rust use statement"},
            {"from": "// {comment}",                 "to": "// {comment}",                   "why": "Same line comment syntax"},
            {"from": "null / undefined",             "to": "None",                            "why": "TS null/undefined -> Rust Option::None"},
        ],
        "types": [
            {"from": "number",          "to": "f64 or i32",            "why": "TS number is float64; in Rust pick the right numeric type"},
            {"from": "string",          "to": "&str or String",         "why": "TS string -> Rust &str (borrowed) or String (owned)"},
            {"from": "boolean",         "to": "bool",                   "why": "Same concept, Rust uses bool"},
            {"from": "Array<T>",        "to": "Vec<T>",                 "why": "TS Array -> Rust Vec (heap-allocated dynamic array)"},
            {"from": "Record<K, V>",    "to": "HashMap<K, V>",          "why": "TS Record -> Rust HashMap"},
            {"from": "T | null",        "to": "Option<T>",              "why": "Nullable TS type -> Rust Option<T>"},
            {"from": "T | Error",       "to": "Result<T, E>",           "why": "Union with error -> Rust Result type"},
        ],
        "l7_note": "Avali->Runethic rotation: typed context/I/O (AV) becomes binding/ownership policy (RU). TypeScript's type system becomes Rust's borrow checker — ownership is the ultimate type safety.",
    },
}

# All primary pairs available
ALL_PAIRS = list(SWAP_TABLES.keys())

# ---------------------------------------------------------------------------
# Commerce examples in each tongue's native language
# (charge_card function — same algorithm, 6 implementations)
# ---------------------------------------------------------------------------

COMMERCE_NATIVE = {
    "KO": {
        "name": "charge_card (Python/Kor'aelin)",
        "prompt": "Write a function to charge a card via Stripe in Python with the $3 profit floor check.",
        "code": '''\
import stripe, os
stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

MIN_PROFIT_CENTS = 300  # $3.00 hard floor — Runethic policy

def charge_card(amount_cents: int, cost_cents: int, payment_method_id: str) -> dict:
    """Charge only if offer clears the profit floor."""
    floor_cents = cost_cents + MIN_PROFIT_CENTS
    if amount_cents < floor_cents:
        return {"success": False, "error": f"Below floor: ${floor_cents/100:.2f} minimum"}
    try:
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency="usd",
            payment_method=payment_method_id,
            confirm=True,
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
        )
        return {"success": True, "payment_intent_id": intent.id}
    except stripe.error.CardError as e:
        return {"success": False, "error": e.user_message}
''',
        "english": "This Python function checks the $3 profit floor before touching Stripe. If the offer is too low it returns a soft error immediately — no API call made. If it clears the floor it creates a PaymentIntent, confirms it in one call, and returns the confirmation ID.",
    },
    "AV": {
        "name": "chargeCard (TypeScript/Avali)",
        "prompt": "Write a chargeCard function in TypeScript that enforces a $3 profit floor before charging via Stripe.",
        "code": '''\
import Stripe from "stripe";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, { apiVersion: "2024-12-18.acacia" });

const MIN_PROFIT_CENTS = 300; // $3.00 hard floor — Runethic policy

interface ChargeResult {
  success: boolean;
  paymentIntentId?: string;
  error?: string;
}

async function chargeCard(
  amountCents: number,
  costCents: number,
  paymentMethodId: string
): Promise<ChargeResult> {
  const floorCents = costCents + MIN_PROFIT_CENTS;
  if (amountCents < floorCents) {
    return { success: false, error: `Below floor: $${(floorCents / 100).toFixed(2)} minimum` };
  }
  try {
    const intent = await stripe.paymentIntents.create({
      amount: amountCents,
      currency: "usd",
      payment_method: paymentMethodId,
      confirm: true,
      automatic_payment_methods: { enabled: true, allow_redirects: "never" },
    });
    return { success: true, paymentIntentId: intent.id };
  } catch (e: any) {
    return { success: false, error: e.message };
  }
}
''',
        "english": "The TypeScript version adds an interface to define what the result object looks like — this is the Avali context layer: explicit I/O schema. The floor check is identical logic, and async/await handles the Promise returned by the Stripe SDK. The type system catches misuse at compile time.",
    },
    "RU": {
        "name": "charge_card (Rust/Runethic)",
        "prompt": "Write a charge_card function in Rust that enforces a $3 profit floor. Use the stripe crate.",
        "code": '''\
use stripe::{Client, CreatePaymentIntent, Currency, PaymentIntent, PaymentIntentConfirmParams};
use std::env;

const MIN_PROFIT_CENTS: i64 = 300; // $3.00 hard floor — Runethic policy

#[derive(Debug)]
pub enum ChargeError {
    BelowFloor(i64),
    StripeError(String),
}

pub async fn charge_card(
    amount_cents: i64,
    cost_cents: i64,
    payment_method_id: &str,
) -> Result<String, ChargeError> {
    let floor_cents = cost_cents + MIN_PROFIT_CENTS;
    if amount_cents < floor_cents {
        return Err(ChargeError::BelowFloor(floor_cents));
    }
    let secret_key = env::var("STRIPE_SECRET_KEY").expect("STRIPE_SECRET_KEY must be set");
    let client = Client::new(secret_key);
    let mut params = CreatePaymentIntent::new(amount_cents, Currency::USD);
    params.payment_method = Some(payment_method_id.into());
    params.confirm = Some(true);
    let intent = PaymentIntent::create(&client, params)
        .await
        .map_err(|e| ChargeError::StripeError(e.to_string()))?;
    Ok(intent.id.to_string())
}
''',
        "english": "The Rust version makes the floor policy compile-time enforced — ChargeError::BelowFloor is a typed error variant, not just a string. The ? operator propagates errors without try/catch boilerplate. Ownership means no accidental double-charges: the PaymentIntent moves through the pipeline exactly once.",
    },
    "CA": {
        "name": "charge_card (C/Cassisivadan)",
        "prompt": "Write a C function that checks a profit floor and calls a Stripe-like payment API via libcurl.",
        "code": '''\
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <curl/curl.h>

#define MIN_PROFIT_CENTS 300  /* $3.00 hard floor -- Runethic policy */

typedef struct {
    int success;
    char payment_id[64];
    char error[256];
} ChargeResult;

ChargeResult charge_card(int amount_cents, int cost_cents, const char* payment_method_id) {
    ChargeResult result = {0};
    int floor_cents = cost_cents + MIN_PROFIT_CENTS;

    if (amount_cents < floor_cents) {
        result.success = 0;
        snprintf(result.error, sizeof(result.error),
                 "Below floor: $%.2f minimum", floor_cents / 100.0);
        return result;
    }

    /* Build POST body */
    char post_body[512];
    snprintf(post_body, sizeof(post_body),
             "amount=%d&currency=usd&payment_method=%s&confirm=true",
             amount_cents, payment_method_id);

    CURL* curl = curl_easy_init();
    if (!curl) {
        snprintf(result.error, sizeof(result.error), "curl_easy_init failed");
        return result;
    }
    /* ... set URL, headers, post_body, response handling ... */
    curl_easy_cleanup(curl);
    result.success = 1;
    strncpy(result.payment_id, "pi_simulated", sizeof(result.payment_id) - 1);
    return result;
}
''',
        "english": "The C version shows how close to the metal payment processing actually is. No garbage collector, no exceptions — just structs with fixed-size char arrays, snprintf for safe string formatting, and libcurl for HTTP. The floor check is identical logic but the programmer manually manages every buffer size to prevent overflow attacks.",
    },
    "UM": {
        "name": "charge_card (Julia/Umbroth)",
        "prompt": "Write a charge_card function in Julia that enforces a $3 profit floor and calls the Stripe API.",
        "code": '''\
using HTTP, JSON3

const MIN_PROFIT_CENTS = 300  # $3.00 hard floor -- Runethic policy
const STRIPE_BASE = "https://api.stripe.com/v1"

struct ChargeResult
    success::Bool
    payment_intent_id::Union{String, Nothing}
    error::Union{String, Nothing}
end

function charge_card(amount_cents::Int, cost_cents::Int, payment_method_id::String)::ChargeResult
    floor_cents = cost_cents + MIN_PROFIT_CENTS
    if amount_cents < floor_cents
        return ChargeResult(false, nothing, "Below floor: \\$$(floor_cents/100) minimum")
    end

    secret_key = ENV["STRIPE_SECRET_KEY"]
    body = "amount=$(amount_cents)&currency=usd&payment_method=$(payment_method_id)&confirm=true"

    response = HTTP.post(
        "$(STRIPE_BASE)/payment_intents",
        ["Authorization" => "Bearer $(secret_key)", "Content-Type" => "application/x-www-form-urlencoded"],
        body
    )

    if response.status == 200
        data = JSON3.read(response.body)
        return ChargeResult(true, data["id"], nothing)
    else
        return ChargeResult(false, nothing, "HTTP $(response.status)")
    end
end
''',
        "english": "Julia looks like Python but runs at C speed via JIT compilation. The struct uses Union types for optional fields — similar to TypeScript nullable unions. Julia is popular for numerical computing, so wrapping a financial API feels natural. The type annotations (::Int, ::String) let the compiler optimize aggressively.",
    },
    "DR": {
        "name": "chargeCard (Haskell/Draumric)",
        "prompt": "Write a chargeCard function in Haskell that enforces a $3 profit floor and calls the Stripe API.",
        "code": '''\
module Commerce.Payment where

import Network.HTTP.Simple (httpJSON, parseRequest, setRequestBodyURLEncoded, setRequestHeaders)
import Data.Aeson (Value, (.:))
import System.Environment (getEnv)
import Control.Monad (when)

minProfitCents :: Int
minProfitCents = 300  -- $3.00 hard floor -- Runethic policy

data ChargeResult
    = ChargeSuccess { paymentIntentId :: String }
    | ChargeFailed  { chargeError :: String }
    deriving (Show)

chargeCard :: Int -> Int -> String -> IO ChargeResult
chargeCard amountCents costCents paymentMethodId = do
    let floorCents = costCents + minProfitCents
    if amountCents < floorCents
        then return $ ChargeFailed ("Below floor: $" ++ show (floorCents `div` 100) ++ " minimum")
        else do
            secretKey <- getEnv "STRIPE_SECRET_KEY"
            let body = [ ("amount",          show amountCents)
                       , ("currency",        "usd")
                       , ("payment_method",  paymentMethodId)
                       , ("confirm",         "true") ]
            request <- parseRequest "POST https://api.stripe.com/v1/payment_intents"
            let req = setRequestBodyURLEncoded body
                    $ setRequestHeaders [("Authorization", "Bearer " <> secretKey)] request
            response <- httpJSON req :: IO (Response Value)
            case getResponseStatusCode response of
                200 -> do
                    let pid = getResponseBody response .: "id"
                    return $ ChargeSuccess pid
                code -> return $ ChargeFailed ("HTTP " ++ show code)
''',
        "english": "Haskell models the result as a data type with two constructors — ChargeSuccess or ChargeFailed — making it impossible to confuse them. The do-notation reads like sequential steps but every step is a pure function composition. The type system proves at compile time that you handle both the floor-hold case and the API success/failure case. No runtime surprises.",
    },
}

# ---------------------------------------------------------------------------
# Parallel / async execution operations
# (batch_charge — same algorithm, 6 concurrency models)
# ---------------------------------------------------------------------------

PARALLEL_NATIVE = {
    "KO": {
        "name": "batch_charge asyncio (Python/Kor'aelin)",
        "prompt": "Write a Python async function that charges multiple cards in parallel using asyncio.gather().",
        "code": '''\
import asyncio
import stripe, os
stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

MIN_PROFIT_CENTS = 300  # $3.00 hard floor — Runethic policy

async def _charge_one(amount: int, pm: str, floor: int) -> dict:
    if amount < floor:
        return {"ok": False, "error": "below_floor"}
    try:
        intent = await asyncio.to_thread(
            stripe.PaymentIntent.create,
            amount=amount, currency="usd",
            payment_method=pm, confirm=True,
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
        )
        return {"ok": True, "id": intent.id}
    except stripe.error.CardError as e:
        return {"ok": False, "error": e.code}

async def batch_charge(orders: list[dict], cost_cents: int) -> list[dict]:
    """Fire all charges concurrently. Each order: {"amount": int, "pm": str}."""
    floor = cost_cents + MIN_PROFIT_CENTS
    return await asyncio.gather(*[_charge_one(o["amount"], o["pm"], floor) for o in orders])
''',
        "english": "Python uses asyncio.gather() to fan out N coroutines in a single event-loop tick. asyncio.to_thread() wraps the blocking Stripe SDK call so it doesn't stall the loop. Each charge runs concurrently — if one card declines the others still complete. The floor check is per-item, inside each coroutine, so no order bypasses the Runethic policy.",
    },
    "AV": {
        "name": "batchCharge Promise.all (TypeScript/Avali)",
        "prompt": "Write a TypeScript async function that charges multiple cards in parallel using Promise.all().",
        "code": '''\
import Stripe from "stripe";
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, { apiVersion: "2024-12-18.acacia" });

const MIN_PROFIT_CENTS = 300;

interface Order { amount: number; paymentMethod: string; }
interface ChargeResult { ok: boolean; id?: string; error?: string; }

async function chargeOne(order: Order, floor: number): Promise<ChargeResult> {
  if (order.amount < floor) return { ok: false, error: "below_floor" };
  try {
    const intent = await stripe.paymentIntents.create({
      amount: order.amount, currency: "usd",
      payment_method: order.paymentMethod, confirm: true,
      automatic_payment_methods: { enabled: true, allow_redirects: "never" },
    });
    return { ok: true, id: intent.id };
  } catch (e: any) {
    return { ok: false, error: e.message };
  }
}

async function batchCharge(orders: Order[], costCents: number): Promise<ChargeResult[]> {
  const floor = costCents + MIN_PROFIT_CENTS;
  return Promise.all(orders.map(o => chargeOne(o, floor)));
}
''',
        "english": "TypeScript uses Promise.all() — the array of promises runs concurrently in the Node.js event loop. The Stripe SDK is already async-native, so no thread wrapper is needed. Each order is typed via the Order interface, making it impossible to pass a malformed order object at compile time. Promise.all rejects if ANY promise rejects — use Promise.allSettled() to collect all results regardless of individual failures.",
    },
    "RU": {
        "name": "batch_charge tokio join_all (Rust/Runethic)",
        "prompt": "Write a Rust async function that charges multiple cards in parallel using tokio and futures::future::join_all.",
        "code": '''\
use futures::future::join_all;

const MIN_PROFIT_CENTS: i64 = 300;

#[derive(Debug)]
pub enum ChargeError {
    BelowFloor(i64),
    StripeError(String),
}

pub async fn charge_one(amount: i64, pm: String, floor: i64) -> Result<String, ChargeError> {
    if amount < floor {
        return Err(ChargeError::BelowFloor(floor));
    }
    // Stripe async call via tokio-based stripe crate
    tokio::task::yield_now().await; // cooperative yield to scheduler
    Ok(format!("pi_{}", &pm[..4.min(pm.len())]))
}

pub async fn batch_charge(
    orders: Vec<(i64, String)>,
    cost_cents: i64,
) -> Vec<Result<String, ChargeError>> {
    let floor = cost_cents + MIN_PROFIT_CENTS;
    let futures: Vec<_> = orders
        .into_iter()
        .map(|(amount, pm)| charge_one(amount, pm, floor))
        .collect();
    join_all(futures).await
}
''',
        "english": "Rust's tokio runtime polls all futures concurrently in a thread pool — join_all collects every Result, success or error, without panicking. Ownership means each order is moved into its own future; no shared mutable state, no data races by construction. ChargeError::BelowFloor is a typed variant — impossible to confuse a floor rejection with a Stripe network error at the call site.",
    },
    "CA": {
        "name": "batch_charge pthreads (C/Cassisivadan)",
        "prompt": "Write a C function that charges multiple cards in parallel using POSIX threads (pthreads).",
        "code": '''\
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>

#define MIN_PROFIT_CENTS 300

typedef struct {
    int amount_cents;
    int cost_cents;
    const char* payment_method;
    /* outputs — written by thread */
    int success;
    char result_id[64];
    char error[128];
} ChargeTask;

static void* charge_thread(void* arg) {
    ChargeTask* t = (ChargeTask*)arg;
    int floor = t->cost_cents + MIN_PROFIT_CENTS;
    if (t->amount_cents < floor) {
        t->success = 0;
        snprintf(t->error, sizeof(t->error), "below_floor: min=%d", floor);
        return NULL;
    }
    /* ... libcurl Stripe HTTP call ... */
    t->success = 1;
    snprintf(t->result_id, sizeof(t->result_id), "pi_%s", t->payment_method);
    return NULL;
}

void batch_charge(ChargeTask* tasks, int n) {
    pthread_t* threads = malloc(n * sizeof(pthread_t));
    for (int i = 0; i < n; i++)
        pthread_create(&threads[i], NULL, charge_thread, &tasks[i]);
    for (int i = 0; i < n; i++)
        pthread_join(threads[i], NULL);
    free(threads);
}
''',
        "english": "C parallelism is fully explicit: malloc a thread handle per order, pthread_create launches each charge_thread, pthread_join waits for all to finish. The ChargeTask struct carries both input and output — each thread writes its result directly into the struct. No garbage collector, no runtime — you own every byte. Buffer sizes are fixed; snprintf prevents overflow. Two loops: one to launch, one to join — the join loop is the synchronization barrier.",
    },
    "UM": {
        "name": "batch_charge Threads.@threads (Julia/Umbroth)",
        "prompt": "Write a Julia function that charges multiple cards in parallel using Threads.@threads.",
        "code": '''\
using HTTP, JSON3

const MIN_PROFIT_CENTS = 300

struct ChargeResult
    success::Bool
    payment_intent_id::Union{String, Nothing}
    error::Union{String, Nothing}
end

function charge_one(amount::Int, cost::Int, pm::String)::ChargeResult
    floor_cents = cost + MIN_PROFIT_CENTS
    amount < floor_cents && return ChargeResult(false, nothing, "below_floor: min=$(floor_cents)")
    secret = ENV["STRIPE_SECRET_KEY"]
    body = "amount=$(amount)&currency=usd&payment_method=$(pm)&confirm=true"
    resp = HTTP.post(
        "https://api.stripe.com/v1/payment_intents",
        ["Authorization" => "Bearer $(secret)", "Content-Type" => "application/x-www-form-urlencoded"],
        body,
    )
    resp.status == 200 ? ChargeResult(true, JSON3.read(resp.body)["id"], nothing) :
                         ChargeResult(false, nothing, "HTTP $(resp.status)")
end

function batch_charge(orders::Vector{Dict}, cost_cents::Int)::Vector{ChargeResult}
    results = Vector{ChargeResult}(undef, length(orders))
    Threads.@threads for i in eachindex(orders)
        results[i] = charge_one(orders[i]["amount"], cost_cents, orders[i]["payment_method"])
    end
    results
end
''',
        "english": "Julia's Threads.@threads macro distributes loop iterations across the thread pool (set JULIA_NUM_THREADS at startup). The results vector is pre-allocated — each thread writes to its own index, so no synchronization needed. Julia compiles this to parallel native code via LLVM; throughput matches C pthreads. For I/O-heavy workloads, @async/@sync gives cooperative concurrency instead of spawning OS threads.",
    },
    "DR": {
        "name": "batchCharge mapConcurrently (Haskell/Draumric)",
        "prompt": "Write a Haskell function that charges multiple cards concurrently using Control.Concurrent.Async.",
        "code": '''\
module Commerce.Batch where

import Control.Concurrent.Async (mapConcurrently)
import System.Environment (getEnv)

minProfitCents :: Int
minProfitCents = 300  -- $3.00 hard floor — Runethic policy

data ChargeResult
    = ChargeSuccess { paymentIntentId :: String }
    | BelowFloor    { minimumCents :: Int }
    | ChargeFailed  { chargeError :: String }
    deriving (Show)

chargeOne :: Int -> Int -> String -> IO ChargeResult
chargeOne amountCents costCents pm = do
    let floorCents = costCents + minProfitCents
    if amountCents < floorCents
        then return $ BelowFloor floorCents
        else do
            secretKey <- getEnv "STRIPE_SECRET_KEY"
            -- ... HTTP.Simple POST to Stripe ...
            return $ ChargeSuccess ("pi_haskell_" ++ take 4 pm)

batchCharge :: [(Int, String)] -> Int -> IO [ChargeResult]
batchCharge orders costCents =
    mapConcurrently (\\(amount, pm) -> chargeOne amount costCents pm) orders
''',
        "english": "Haskell's mapConcurrently (from the async library) forks one green thread per element, runs them concurrently, then collects results in input order. Purity means no shared mutable state exists by default — the only side effect is the Stripe HTTP call wrapped in IO. ChargeResult is a sum type with three constructors: ChargeSuccess, BelowFloor, ChargeFailed — pattern matching at the call site forces you to handle all three cases.",
    },
}

# ---------------------------------------------------------------------------
# Concurrency primitive swap tables (parallel execution translation)
# ---------------------------------------------------------------------------

CONCURRENCY_SWAPS = {
    ("KO", "AV"): {
        "primitives": [
            {"from": "asyncio.gather(*coroutines)",          "to": "Promise.all(promises)",               "why": "Both fan out N async tasks and collect results in one call"},
            {"from": "asyncio.to_thread(blocking_fn, *args)","to": "(not needed — SDK is async-native)",  "why": "Stripe TS SDK returns Promises natively; no thread wrapper required"},
            {"from": "async def fn() -> T:",                 "to": "async function fn(): Promise<T> {",   "why": "async keyword on both; TS requires explicit Promise<T> return type"},
            {"from": "await coroutine",                      "to": "await promise",                        "why": "Identical await syntax; resolves the pending async value"},
            {"from": "asyncio.create_task(coro)",            "to": "/* implicit — Promises are eager */", "why": "JS Promises start executing on creation; no explicit task launch"},
            {"from": "asyncio.gather(..., return_exceptions=True)", "to": "Promise.allSettled(promises)", "why": "Collect all results even if some fail; allSettled never rejects"},
            {"from": "asyncio.run(main())",                  "to": "main().catch(console.error)",         "why": "Entry point for async main; TS/Node uses .catch for top-level errors"},
        ],
        "error_model": [
            {"from": "asyncio.gather(*tasks)  # raises on first failure", "to": "Promise.all(promises)  # rejects on first failure", "why": "Default gather/all: fail-fast — one failure cancels the batch result"},
            {"from": "asyncio.gather(return_exceptions=True)",             "to": "Promise.allSettled(promises)",                       "why": "Tolerant batch: collect all results including errors"},
        ],
        "l7_note": "KO->AV parallel: Python's asyncio and Node.js V8 are both single-threaded event loops. gather() and Promise.all() are isomorphic — a Mobius rotation in tongue space with no semantic loss.",
    },
    ("KO", "RU"): {
        "primitives": [
            {"from": "asyncio.gather(*coros)",                "to": "join_all(futures).await",              "why": "join_all from the futures crate polls all futures concurrently"},
            {"from": "asyncio.to_thread(blocking_fn)",        "to": "tokio::task::spawn_blocking(fn)",      "why": "Both offload blocking calls to a thread pool"},
            {"from": "async def fn() -> T:",                  "to": "async fn fn() -> T {",                 "why": "Same async keyword; Rust infers return type via -> T"},
            {"from": "await coroutine",                       "to": "future.await",                         "why": "Rust uses postfix .await — semantically identical"},
            {"from": "asyncio.create_task(coro)",             "to": "tokio::spawn(future)",                 "why": "Spawn a concurrent task on the tokio runtime"},
            {"from": "concurrent.futures.ThreadPoolExecutor", "to": "rayon::ThreadPool",                    "why": "CPU-bound parallelism: Python threadpool vs Rayon data-parallel"},
            {"from": "list(executor.map(fn, items))",         "to": "items.par_iter().map(fn).collect()",  "why": "Parallel map over a collection"},
        ],
        "error_model": [
            {"from": "except Exception as e:",               "to": "Err(e) => { ... }",                    "why": "Rust errors are values (Result<T,E>); no exception stack unwinding"},
            {"from": "asyncio.gather(return_exceptions=True)","to": "join_all collects all Results",         "why": "join_all collects Ok and Err without panicking"},
        ],
        "l7_note": "KO->RU parallel: Python asyncio is I/O concurrency only (GIL prevents CPU parallelism). Rust tokio is fully multi-threaded and rayon par_iter gives data parallelism that asyncio cannot match.",
    },
    ("KO", "CA"): {
        "primitives": [
            {"from": "asyncio.gather(*tasks)",               "to": "pthread_create() x N + pthread_join() x N", "why": "C has no event loop; real OS threads, one per task, explicitly joined"},
            {"from": "async def fn():",                      "to": "void* fn(void* arg)",                   "why": "Thread function signature: void* in, void* out; cast to your struct"},
            {"from": "await fn()",                          "to": "pthread_join(tid, NULL)",                "why": "join blocks the caller until the thread finishes — equivalent to await"},
            {"from": "asyncio.Queue()",                     "to": "pthread_mutex_t + pthread_cond_t",      "why": "No built-in async queue; protect shared data with mutex + condition variable"},
            {"from": "loop.run_in_executor(pool, fn)",      "to": "pthread_create() with pooled thread",   "why": "Both dispatch work outside the main thread"},
        ],
        "error_model": [
            {"from": "except Exception",                    "to": "check return value / errno",            "why": "C has no exceptions; check errno or function return codes"},
            {"from": "task.result()",                       "to": "*(ResultType*)retval after pthread_join","why": "Cast the void* returned via pthread_exit to get the result struct"},
        ],
        "l7_note": "KO->CA parallel: Python abstracts threads behind coroutines. C exposes raw OS threads — pthread_t, mutex, condition variable are all manual. Maximum control, maximum responsibility.",
    },
    ("KO", "UM"): {
        "primitives": [
            {"from": "asyncio.gather(*coros)",              "to": "@sync begin; @async fn() for ... end", "why": "Julia @async launches a Task, @sync waits for all Tasks in its scope"},
            {"from": "for item in items: create_task(fn(item))", "to": "Threads.@threads for item in items", "why": "Parallel for: asyncio tasks -> Julia threaded loop (true OS threads)"},
            {"from": "ProcessPoolExecutor.map(fn, items)",  "to": "pmap(fn, items)",                      "why": "Distributed/multi-process parallel map"},
            {"from": "asyncio.Queue()",                     "to": "Channel{T}(n)",                        "why": "Async-safe FIFO: asyncio.Queue -> Julia Channel with buffer size n"},
            {"from": "asyncio.Lock()",                      "to": "ReentrantLock()",                      "why": "Mutual exclusion; same semantics, different name"},
            {"from": "await asyncio.sleep(n)",              "to": "sleep(n)",                             "why": "Suspend a task; Julia sleep is cooperative inside @async context"},
        ],
        "error_model": [
            {"from": "try: await fn() except E as e:",     "to": "try\n    fn()\ncatch e::E",            "why": "Julia try/catch with type assertion works inside @async tasks"},
        ],
        "l7_note": "KO->UM parallel: Julia Threads.@threads gives true CPU parallelism — Python asyncio is I/O-only. Julia is built for numerical parallel computing; Threads.@threads on a batch loop matches C pthread throughput.",
    },
    ("KO", "DR"): {
        "primitives": [
            {"from": "asyncio.gather(*coros)",              "to": "mapConcurrently fn items",             "why": "mapConcurrently (async lib): parallel map, results collected in order"},
            {"from": "asyncio.create_task(coro)",           "to": "async action",                         "why": "async from Control.Concurrent.Async launches a green thread"},
            {"from": "await task",                          "to": "wait asyncHandle",                     "why": "wait blocks until the async action completes and returns its value"},
            {"from": "asyncio.Queue()",                     "to": "newTChanIO  -- STM channel",           "why": "Software Transactional Memory channel: composable, deadlock-free"},
            {"from": "asyncio.Lock()",                      "to": "newMVar ()  -- MVar as mutex",         "why": "Empty MVar as a mutex: takeMVar locks, putMVar unlocks"},
            {"from": "executor.map(fn, xs)",                "to": "mapConcurrently fn xs",                "why": "Both apply fn to each element concurrently and collect results"},
        ],
        "error_model": [
            {"from": "asyncio.gather(return_exceptions=True)", "to": "mapConcurrently wrapped in try",   "why": "Haskell IO exceptions are catchable; wrap each action in try from Control.Exception"},
        ],
        "l7_note": "KO->DR parallel: Haskell green threads are cheaper than OS threads. STM (Software Transactional Memory) gives composable, deadlock-free shared state — more powerful than Python asyncio.Lock.",
    },
}


def _concurrency_model(tongue: str) -> str:
    models = {
        "KO": "single-threaded async event loop (asyncio), I/O concurrency only due to GIL",
        "AV": "single-threaded async event loop (V8/Node.js), Promise-based I/O concurrency",
        "RU": "multi-threaded async runtime (tokio) + data-parallel CPU (rayon), no GIL",
        "CA": "raw OS threads (pthreads), manual synchronization, direct CPU access",
        "UM": "multi-threaded JIT (Threads.@threads) + distributed compute (pmap), BLAS-aware",
        "DR": "green threads (forkIO) + composable STM for shared state, no deadlocks",
    }
    return models.get(tongue, "unknown model")


def _throughput_note(src: str, dst: str) -> str:
    notes = {
        ("KO", "AV"): "Equivalent for I/O-bound tasks; both are single-threaded event loops",
        ("KO", "RU"): "Rust tokio parallelizes CPU work; Python asyncio cannot (GIL) — use rayon for CPU-bound",
        ("KO", "CA"): "C pthreads are OS threads with no runtime overhead; faster for CPU-heavy work",
        ("KO", "UM"): "Julia Threads.@threads provides true CPU parallelism vs Python I/O-only asyncio",
        ("KO", "DR"): "Haskell green threads are cheaper than OS threads; STM eliminates deadlock risk",
        ("AV", "RU"): "Rust tokio parallelizes CPU work that Node.js single-thread cannot",
    }
    return notes.get((src, dst), notes.get((dst, src), "context-dependent; benchmark with your workload"))


# ---------------------------------------------------------------------------
# SCBE record construction
# ---------------------------------------------------------------------------

VERSION = "3.3.0"
SOURCE = "scbe_aethermoore"
AUTHOR = "Issac Davis"


def source_hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:8]


def make_system_header(weights: dict, layers: list, axioms: list, difficulty: float, record_type: str) -> str:
    tongue_str = " ".join(f"{k}={v:.3f}" for k, v in weights.items())
    layer_str = " ".join(f"L{l}" for l in sorted(layers))
    axiom_str = " ".join(axioms)
    return (
        f"[TONGUES: {tongue_str}]\n"
        f"[LAYERS: {layer_str}]\n"
        f"[AXIOMS: {axiom_str}]\n"
        f"[DIFFICULTY: {difficulty:.3f}]\n"
        f"[RECORD_TYPE: {record_type}]\n"
        f"You are a polyglot programming assistant trained on the Sacred Tongue language system. "
        f"Each programming language corresponds to a Sacred Tongue. "
        f"KO=Python AV=TypeScript RU=Rust CA=C UM=Julia DR=Haskell. "
        f"When tongue weights shift, you translate code between the corresponding languages "
        f"using the command swap guide as your transformation rule."
    )


def make_native_record(tongue: str, example: dict) -> dict:
    """TYPE-N: Code in tongue X's native language. High X weight."""
    weights = native_weights(tongue)
    layers = [1, 2, 3, 4]  # ingestion through weighted transform
    axioms = ["composition", "unitarity"]
    diff = round(0.40 + random.uniform(-0.05, 0.05), 3)

    system = make_system_header(weights, layers, axioms, diff, "NATIVE")
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": example["prompt"]},
            {"role": "assistant", "content": example["code"]},
        ],
        "tongue_weights": weights,
        "dominant_tongue": tongue,
        "lang": LANG_MAP[tongue],
        "layers": sorted(layers),
        "axioms": axioms,
        "difficulty": diff,
        "record_type": "NATIVE",
        "augmentation": "polyglot_sft",
        "tags": ["polyglot", "native", tongue, LANG_MAP[tongue].lower(), "commerce"],
        "source_hash": source_hash(example["prompt"]),
        "metadata": {"source": SOURCE, "version": VERSION, "author": AUTHOR},
    }


def make_swap_record(src: str, dst: str) -> dict:
    """TYPE-S: The swap guide itself. Equal src/dst weights (Mobius midpoint at L7)."""
    table = SWAP_TABLES.get((src, dst))
    if not table:
        return None

    weights = transition_weights(src, dst)
    layers = [3, 7]  # weighted transform + Mobius phase
    axioms = ["symmetry", "composition"]
    diff = round(0.55 + random.uniform(-0.05, 0.05), 3)

    src_lang = LANG_MAP[src]
    dst_lang = LANG_MAP[dst]
    src_name = TONGUE_FULL[src]
    dst_name = TONGUE_FULL[dst]

    # Build the swap guide as a readable reference
    guide_lines = [
        f"# Command Swap Guide: {src_lang} ({src_name}) -> {dst_lang} ({dst_name})",
        f"# L7 Mobius Rotation: {src}={weights[src]:.3f} <-> {dst}={weights[dst]:.3f}",
        "",
        "## Syntax Swaps",
    ]
    for rule in table.get("syntax", []):
        guide_lines.append(f'  "{rule["from"]}"')
        guide_lines.append(f'  -> "{rule["to"]}"')
        guide_lines.append(f'  # {rule["why"]}')
        guide_lines.append("")

    if "types" in table:
        guide_lines.append("## Type Swaps")
        for rule in table["types"]:
            guide_lines.append(f'  {src_lang}: {rule["from"]}  ->  {dst_lang}: {rule["to"]}')
            guide_lines.append(f'  # {rule["why"]}')
        guide_lines.append("")

    for extra_key in ("naming", "ownership", "memory"):
        if extra_key in table:
            guide_lines.append(f"## {extra_key.title()} Notes")
            for rule in table[extra_key]:
                guide_lines.append(f'  {rule["from"]}  ->  {rule["to"]}')
                guide_lines.append(f'  # {rule["why"]}')
            guide_lines.append("")

    guide_lines.append(f"## Geometric Note")
    guide_lines.append(f"  {table['l7_note']}")

    guide_text = "\n".join(guide_lines)

    prompt = (
        f"Give me the complete command swap guide for converting {src_lang} code to {dst_lang}. "
        f"Show the syntax substitutions, type mapping, and any language-specific rules."
    )

    system = make_system_header(weights, layers, axioms, diff, "SWAP_GUIDE")
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
            {"role": "assistant", "content": guide_text},
        ],
        "tongue_weights": weights,
        "dominant_tongue": None,  # transition state — no dominant
        "src_tongue": src,
        "dst_tongue": dst,
        "src_lang": src_lang,
        "dst_lang": dst_lang,
        "layers": sorted(layers),
        "axioms": axioms,
        "difficulty": diff,
        "record_type": "SWAP_GUIDE",
        "augmentation": "polyglot_sft",
        "tags": ["polyglot", "swap_guide", src, dst, src_lang.lower(), dst_lang.lower()],
        "source_hash": source_hash(prompt),
        "metadata": {"source": SOURCE, "version": VERSION, "author": AUTHOR},
    }


def make_translation_record(src: str, dst: str) -> dict:
    """TYPE-T: Given code in src + swap guide, produce dst. Weights shift src->dst."""
    src_example = COMMERCE_NATIVE.get(src)
    dst_example = COMMERCE_NATIVE.get(dst)
    if not src_example or not dst_example:
        return None

    table = SWAP_TABLES.get((src, dst))
    guide_note = table.get("l7_note", "") if table else ""

    weights = result_weights(dst)
    layers = [3, 7, 12]  # weighted transform + Mobius + harmonic wall (transition enforced)
    axioms = ["symmetry", "unitarity", "composition"]
    diff = round(0.65 + random.uniform(-0.05, 0.05), 3)

    src_lang = LANG_MAP[src]
    dst_lang = LANG_MAP[dst]

    prompt = (
        f"Convert the following {src_lang} code to {dst_lang} using the command swap guide.\n"
        f"Apply every syntax, type, and naming substitution from the {src_lang}->{dst_lang} swap guide.\n\n"
        f"```{src_lang.lower()}\n{src_example['code']}\n```\n\n"
        f"Produce the equivalent {dst_lang} implementation with the same profit floor logic intact."
    )

    explanation = (
        f"{dst_example['english']}\n\n"
        f"Geometric note: {guide_note}"
    )

    system = make_system_header(weights, layers, axioms, diff, "TRANSLATE")
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
            {"role": "assistant", "content": f"```{dst_lang.lower()}\n{dst_example['code']}\n```\n\n{explanation}"},
        ],
        "tongue_weights": weights,
        "dominant_tongue": dst,
        "src_tongue": src,
        "dst_tongue": dst,
        "layers": sorted(layers),
        "axioms": axioms,
        "difficulty": diff,
        "record_type": "TRANSLATE",
        "augmentation": "polyglot_sft",
        "tags": ["polyglot", "translation", src, dst, src_lang.lower(), dst_lang.lower(), "commerce"],
        "source_hash": source_hash(prompt),
        "metadata": {"source": SOURCE, "version": VERSION, "author": AUTHOR},
    }


def make_parallel_record(tongue: str, example: dict) -> dict:
    """TYPE-P: Parallel/async version of an operation in tongue X's native concurrency model."""
    weights = native_weights(tongue)
    layers = [3, 6, 8, 9]  # weighted transform + breathing (temporal) + Hamiltonian + spectral
    axioms = ["causality", "composition", "locality"]
    diff = round(0.70 + random.uniform(-0.05, 0.05), 3)

    system = make_system_header(weights, layers, axioms, diff, "PARALLEL")
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": example["prompt"]},
            {"role": "assistant", "content": example["code"]},
        ],
        "tongue_weights": weights,
        "dominant_tongue": tongue,
        "lang": LANG_MAP[tongue],
        "layers": sorted(layers),
        "axioms": axioms,
        "difficulty": diff,
        "record_type": "PARALLEL",
        "augmentation": "polyglot_sft",
        "tags": ["polyglot", "parallel", "async", "concurrency", tongue, LANG_MAP[tongue].lower()],
        "source_hash": source_hash(example["prompt"]),
        "metadata": {"source": SOURCE, "version": VERSION, "author": AUTHOR},
    }


def make_concurrency_swap_record(src: str, dst: str) -> dict:
    """TYPE-CS: Concurrency primitive swap guide — how async/parallel patterns translate between tongues."""
    table = CONCURRENCY_SWAPS.get((src, dst))
    if not table:
        return None

    weights = transition_weights(src, dst)
    layers = [3, 6, 7, 8]  # weighted + breathing (causality) + Mobius (rotation) + Hamiltonian
    axioms = ["causality", "symmetry", "composition"]
    diff = round(0.75 + random.uniform(-0.05, 0.05), 3)

    src_lang = LANG_MAP[src]
    dst_lang = LANG_MAP[dst]

    guide_lines = [
        f"# Concurrency Swap Guide: {src_lang} ({TONGUE_FULL[src]}) -> {dst_lang} ({TONGUE_FULL[dst]})",
        f"# Parallel execution pattern translation at L6/L7 (breathing + Mobius rotation)",
        f"# {src}: {_concurrency_model(src)}",
        f"# {dst}: {_concurrency_model(dst)}",
        "",
        "## Concurrency Primitives",
    ]
    for rule in table.get("primitives", []):
        guide_lines.append(f'  {src_lang}: {rule["from"]}')
        guide_lines.append(f'  -> {dst_lang}: {rule["to"]}')
        guide_lines.append(f'  # {rule["why"]}')
        guide_lines.append("")

    if "error_model" in table:
        guide_lines.append("## Error Handling in Parallel Context")
        for rule in table["error_model"]:
            guide_lines.append(f'  {src_lang}: {rule["from"]}')
            guide_lines.append(f'  -> {dst_lang}: {rule["to"]}')
            guide_lines.append(f'  # {rule["why"]}')
        guide_lines.append("")

    guide_lines.append("## Geometric Note")
    guide_lines.append(f"  {table['l7_note']}")

    guide_text = "\n".join(guide_lines)

    prompt = (
        f"How do I translate parallel and async execution patterns from {src_lang} to {dst_lang}? "
        f"Show the concurrency primitives and how they map between the two languages."
    )

    system = make_system_header(weights, layers, axioms, diff, "CONCURRENCY_SWAP")
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
            {"role": "assistant", "content": guide_text},
        ],
        "tongue_weights": weights,
        "dominant_tongue": None,
        "src_tongue": src,
        "dst_tongue": dst,
        "src_lang": src_lang,
        "dst_lang": dst_lang,
        "layers": sorted(layers),
        "axioms": axioms,
        "difficulty": diff,
        "record_type": "CONCURRENCY_SWAP",
        "augmentation": "polyglot_sft",
        "tags": ["polyglot", "concurrency", "parallel", "async", src, dst, src_lang.lower(), dst_lang.lower()],
        "source_hash": source_hash(prompt),
        "metadata": {"source": SOURCE, "version": VERSION, "author": AUTHOR},
    }


def make_cross_parallel_record(src: str, dst: str) -> dict:
    """TYPE-XP: Cross-domain parallel comparison — same concurrent batch pattern, two tongues side by side."""
    src_example = PARALLEL_NATIVE.get(src)
    dst_example = PARALLEL_NATIVE.get(dst)
    if not src_example or not dst_example:
        return None

    weights = transition_weights(src, dst)
    layers = [3, 5, 6, 7, 8]  # weighted + hyperbolic + breathing + Mobius + Hamiltonian
    axioms = ["causality", "symmetry"]
    diff = round(0.72 + random.uniform(-0.05, 0.05), 3)

    src_lang = LANG_MAP[src]
    dst_lang = LANG_MAP[dst]

    prompt = (
        f"Compare how {src_lang} and {dst_lang} implement concurrent batch charging. "
        f"What is the fundamental concurrency model of each, and what stays the same across both?"
    )

    response = (
        f"## Cross-Domain Parallel Execution: {src_lang} vs {dst_lang}\n\n"
        f"### {src_lang} ({TONGUE_FULL[src]}) — {_concurrency_model(src)}\n"
        f"```{src_lang.lower()}\n{src_example['code']}\n```\n"
        f"{src_example['english']}\n\n"
        f"### {dst_lang} ({TONGUE_FULL[dst]}) — {_concurrency_model(dst)}\n"
        f"```{dst_lang.lower()}\n{dst_example['code']}\n```\n"
        f"{dst_example['english']}\n\n"
        f"## What is invariant (RU-policy, regardless of tongue)\n"
        f"- `floor = cost + {300}` enforced per-item BEFORE any API call\n"
        f"- Failed items do not block other items — partial success is valid\n"
        f"- Results are collected in input order even when execution is concurrent\n"
        f"- The profit floor is code-enforced, NOT delegated to the payment API\n\n"
        f"## Concurrency model differences\n"
        f"- {src_lang}: {_concurrency_model(src)}\n"
        f"- {dst_lang}: {_concurrency_model(dst)}\n"
        f"- Throughput note: {_throughput_note(src, dst)}\n"
    )

    system = make_system_header(weights, layers, axioms, diff, "CROSS_PARALLEL")
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
            {"role": "assistant", "content": response},
        ],
        "tongue_weights": weights,
        "dominant_tongue": None,
        "src_tongue": src,
        "dst_tongue": dst,
        "layers": sorted(layers),
        "axioms": axioms,
        "difficulty": diff,
        "record_type": "CROSS_PARALLEL",
        "augmentation": "polyglot_sft",
        "tags": ["polyglot", "cross_parallel", "concurrency", src, dst, "commerce"],
        "source_hash": source_hash(prompt),
        "metadata": {"source": SOURCE, "version": VERSION, "author": AUTHOR},
    }


def make_cross_domain_record(concept: str, src: str, dst: str) -> dict:
    """TYPE-X: Same concept, two languages — shows pattern invariance."""
    src_example = COMMERCE_NATIVE.get(src)
    dst_example = COMMERCE_NATIVE.get(dst)
    if not src_example or not dst_example:
        return None

    weights = transition_weights(src, dst)
    layers = [3, 5, 7]  # weighted + hyperbolic distance + Mobius
    axioms = ["symmetry"]
    diff = round(0.50 + random.uniform(-0.05, 0.05), 3)

    src_lang = LANG_MAP[src]
    dst_lang = LANG_MAP[dst]

    prompt = (
        f"Show the profit floor enforcement pattern in both {src_lang} and {dst_lang}. "
        f"Explain what stays the same across both languages and what changes."
    )

    response = (
        f"## Pattern: Profit Floor Enforcement\n"
        f"The $3 minimum profit floor is a RU (Runethic) policy — it binds regardless of tongue.\n\n"
        f"### {src_lang} ({TONGUE_FULL[src]})\n"
        f"```{src_lang.lower()}\n{src_example['code']}\n```\n"
        f"{src_example['english']}\n\n"
        f"### {dst_lang} ({TONGUE_FULL[dst]})\n"
        f"```{dst_lang.lower()}\n{dst_example['code']}\n```\n"
        f"{dst_example['english']}\n\n"
        f"## What stays the same (RU-invariant)\n"
        f"- floor_cents = cost_cents + 300 (the $3 floor is a constant)\n"
        f"- amount < floor -> early return/error (floor check is first, before any API call)\n"
        f"- The profit floor is enforced in CODE, not by the payment API\n\n"
        f"## What changes (tongue-specific)\n"
        f"- Error handling: {src_lang} uses exceptions / {dst_lang} uses {'Result<T,E>' if dst == 'RU' else 'typed ADT' if dst == 'DR' else 'typed interface'}\n"
        f"- Type annotations: {src_lang} type hints vs {dst_lang} type system\n"
        f"- Naming convention: {src_lang} snake_case vs {dst_lang} {'camelCase' if dst == 'AV' else 'snake_case' if dst == 'RU' else 'camelCase' if dst == 'DR' else 'same'}\n"
    )

    system = make_system_header(weights, layers, axioms, diff, "CROSS_DOMAIN")
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
            {"role": "assistant", "content": response},
        ],
        "tongue_weights": weights,
        "dominant_tongue": None,
        "src_tongue": src,
        "dst_tongue": dst,
        "layers": sorted(layers),
        "axioms": axioms,
        "difficulty": diff,
        "record_type": "CROSS_DOMAIN",
        "augmentation": "polyglot_sft",
        "tags": ["polyglot", "cross_domain", "pattern_invariance", src, dst, "commerce"],
        "source_hash": source_hash(prompt),
        "metadata": {"source": SOURCE, "version": VERSION, "author": AUTHOR},
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(pairs: list, output: str, dry_run: bool) -> None:
    records = []
    type_counts = {}

    # TYPE-N: Native records for each tongue that has an example
    for tongue, example in COMMERCE_NATIVE.items():
        if tongue not in LANG_MAP:
            continue
        r = make_native_record(tongue, example)
        records.append(r)
        type_counts["NATIVE"] = type_counts.get("NATIVE", 0) + 1
        # Also add the English explanation as a plain NATIVE record
        eng_example = dict(example)
        eng_example["code"] = example["english"]
        r2 = make_native_record(tongue, eng_example)
        r2["tags"].append("english")
        records.append(r2)
        type_counts["NATIVE"] = type_counts.get("NATIVE", 0) + 1

    # TYPE-P: Parallel/async records for each tongue
    for tongue, example in PARALLEL_NATIVE.items():
        if tongue not in LANG_MAP:
            continue
        r = make_parallel_record(tongue, example)
        records.append(r)
        type_counts["PARALLEL"] = type_counts.get("PARALLEL", 0) + 1
        # English explanation variant
        eng_example = dict(example)
        eng_example["code"] = example["english"]
        r2 = make_parallel_record(tongue, eng_example)
        r2["tags"].append("english")
        records.append(r2)
        type_counts["PARALLEL"] = type_counts.get("PARALLEL", 0) + 1

    # TYPE-S, TYPE-T, TYPE-X, TYPE-CS, TYPE-XP for each requested pair
    for (src, dst) in pairs:
        # Swap guide
        r = make_swap_record(src, dst)
        if r:
            records.append(r)
            type_counts["SWAP_GUIDE"] = type_counts.get("SWAP_GUIDE", 0) + 1

        # Translation task
        r = make_translation_record(src, dst)
        if r:
            records.append(r)
            type_counts["TRANSLATE"] = type_counts.get("TRANSLATE", 0) + 1

        # Cross-domain comparison (sequential operations)
        r = make_cross_domain_record("profit_floor", src, dst)
        if r:
            records.append(r)
            type_counts["CROSS_DOMAIN"] = type_counts.get("CROSS_DOMAIN", 0) + 1

        # Concurrency primitive swap guide
        r = make_concurrency_swap_record(src, dst)
        if r:
            records.append(r)
            type_counts["CONCURRENCY_SWAP"] = type_counts.get("CONCURRENCY_SWAP", 0) + 1

        # Cross-domain parallel comparison
        r = make_cross_parallel_record(src, dst)
        if r:
            records.append(r)
            type_counts["CROSS_PARALLEL"] = type_counts.get("CROSS_PARALLEL", 0) + 1

    print(f"Polyglot SFT generator")
    print(f"  Pairs: {[f'{s}->{d}' for s,d in pairs]}")
    print(f"  Records: {len(records)}")
    for t, c in sorted(type_counts.items()):
        print(f"    {t}: {c}")

    # Tongue distribution
    tongue_counts: dict = {}
    for r in records:
        dt = r.get("dominant_tongue")
        if dt:
            tongue_counts[dt] = tongue_counts.get(dt, 0) + 1
        else:
            tongue_counts["[transition]"] = tongue_counts.get("[transition]", 0) + 1

    print("\n  Tongue distribution:")
    for t, c in sorted(tongue_counts.items(), key=lambda x: -x[1]):
        lang = LANG_MAP.get(t, t)
        print(f"    {t} ({lang}): {'#'*c} {c}")

    if dry_run:
        print("\nDRY RUN — sample record 0:")
        print(json.dumps(records[0], indent=2, ensure_ascii=False)[:1000])
        return

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n  Written: {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate polyglot cross-language SFT data")
    parser.add_argument(
        "--pairs", nargs="+", default=["KO-AV", "KO-RU", "KO-CA", "KO-UM", "KO-DR"],
        help="Tongue pairs to generate swap guides for (e.g. KO-AV KO-RU AV-RU)"
    )
    parser.add_argument("--all-pairs", action="store_true", help="Generate all defined pairs")
    parser.add_argument(
        "--output", default="training-data/hand_tune/coder/polyglot_sft.jsonl"
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.all_pairs:
        pairs = ALL_PAIRS
    else:
        pairs = []
        for p in args.pairs:
            parts = p.split("-")
            if len(parts) == 2:
                pairs.append((parts[0].upper(), parts[1].upper()))

    run(pairs, args.output, args.dry_run)


if __name__ == "__main__":
    main()
