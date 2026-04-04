#!/usr/bin/env python3
"""Generate Code Substrate L0 Training Data — byte-level programming universals.

Teaches the model what ALL programming languages look like at the binary level:
the 12 invariants, ASCII patterns, delimiter physics, whitespace semantics,
and how bytes become tokens become AST become programs.

Every record is tongue-tagged and shape-engraved for multi-view training.

References:
  - Grok session: "What patterns repeat across all code languages in binary"
  - docs/specs/GEOMETRIC_THOUGHT_EFFICIENCY_TRAINING.md
  - Binary-First Training Stack spec
"""

import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "training-data" / "sft" / "code_substrate_l0_sft.jsonl"

ALL_TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]


def make_record(instruction, output, tongue, category, tongues_active=None):
    active = tongues_active or [tongue]
    null = [t for t in ALL_TONGUES if t not in active]
    return {
        "instruction": instruction,
        "output": output,
        "tongue": tongue,
        "tongues_active": active,
        "tongues_null": null,
        "layer": "L0",
        "category": category,
        "view_type": "null-heavy" if len(null) >= 4 else "partial",
        "governance": "ALLOW",
        "source": "code_substrate_l0_generator",
    }


RECORDS = [
    # ── Invariant 1: The ASCII Cage ──
    make_record(
        "What byte range do all programming languages live in?",
        "Every programming language uses bytes 0x09-0x7E (tab through tilde). That's 95 usable bytes out of 256. Code is SPARSE — 63% of the byte space is never used. This means code occupies a tiny, predictable region of byte space. The model that knows this can immediately reject 63% of byte sequences as 'not code'. Printable ASCII (0x20-0x7E) = 95 chars. Add tab (0x09), newline (0x0A), carriage return (0x0D) = 98 total code-relevant bytes.",
        "CA", "binary_invariant",
    ),
    make_record(
        "Why is code sparse in byte space?",
        "Code uses 95 of 256 possible byte values. The unused 161 bytes (0x00-0x08, 0x0E-0x1F, 0x7F-0xFF) are control characters and extended ASCII that no language keyword or operator uses. This sparsity is a universal invariant: Python, Rust, Go, JavaScript, C, Haskell — all live in the same 95-byte cage. A byte-aware model exploits this: if a byte is outside 0x09-0x7E, it's not code. That's a free 63% filter on the input space.",
        "CA", "binary_invariant",
    ),
    # ── Invariant 2: Delimiter Physics ──
    make_record(
        "What are the universal delimiters across all programming languages?",
        "Six delimiter pairs appear in virtually every language: parentheses 0x28/0x29, square brackets 0x5B/0x5D, curly braces 0x7B/0x7D. These are PAIRED — every opener has a closer. The parser counts nesting depth. Unmatched delimiters are always a syntax error. This nesting rule is universal: Python, JavaScript, Rust, Go, C, Java, Haskell, Lisp — all require balanced delimiters. The nesting depth at any byte position is computable in O(n) and deterministic.",
        "CA", "binary_invariant",
    ),
    make_record(
        "Why do all languages use the same six delimiter bytes?",
        "ASCII only provides three bracket pairs: () [] {}. These were defined in 1963 and every language since has used them because: (1) they're visually distinct, (2) they're on every keyboard, (3) parsers can match them with a single stack. No language has invented new bracket characters — they all share the same 6 bytes. This is a hard constraint of the ASCII encoding, not a design choice. Unicode adds a few more but no mainstream language uses them for parsing.",
        "CA", "binary_invariant", ["CA", "DR"],
    ),
    # ── Invariant 3: Whitespace Semantics ──
    make_record(
        "What do the whitespace bytes mean across programming languages?",
        "Three whitespace bytes carry meaning: Space 0x20 (token separator), Tab 0x09 (indentation unit), Newline 0x0A (statement terminator or separator). Space separates tokens: 'def' + 0x20 + 'add' = two tokens. Without the space, 'defadd' = one token (different meaning). Tab/spaces encode scope in Python (significant whitespace) and are ignored in C/Java/Rust (insignificant). Newline is a statement terminator in Go and Python but ignored in C/Java. The KEY insight: whitespace bytes CHANGE PARSE RESULTS even though they're 'invisible'.",
        "CA", "binary_invariant",
    ),
    make_record(
        "Why does indentation matter at the byte level?",
        "In Python, 4 spaces (0x20 0x20 0x20 0x20) at line start means 'this is inside a block.' Remove one space (0x20 0x20 0x20) and the parser produces a DIFFERENT AST — IndentationError or changed scope. The parser literally counts space bytes. In C/Java/Rust, the same spaces are ignored — braces {} determine scope instead. This means the SAME byte sequence ('    x = 1') has different structural meaning in different languages. The model must know which whitespace regime it's in.",
        "CA", "binary_invariant", ["CA", "DR"],
    ),
    # ── Invariant 4: Quote Pairing ──
    make_record(
        "How do string delimiters work at the byte level?",
        "Two bytes define strings universally: single quote 0x27 and double quote 0x22. Between these bytes, ALL other bytes become literal data, not code. The parser switches mode: outside quotes = code, inside quotes = data. Escape character 0x5C (backslash) lets you embed the quote byte inside the string: 0x22 0x5C 0x22 0x22 = a string containing one double-quote. This quote-mode switching is identical in Python, JavaScript, C, Rust, Go, Java, Ruby, PHP — every language with strings.",
        "CA", "binary_invariant",
    ),
    # ── Invariant 5: Operator Byte Patterns ──
    make_record(
        "How does one byte difference change meaning in code operators?",
        "Assignment = (0x3D) vs equality == (0x3D 0x3D): one extra byte changes 'set this value' to 'check this value'. This is universal across Python, JavaScript, C, Go, Rust. Similarly: < (0x3C) vs <= (0x3C 0x3D) vs << (0x3C 0x3C). The parser resolves this by maximal munch — take the longest matching operator. One byte difference = completely different operation. The model that understands this knows WHY == exists (it's = with a confirmation byte) rather than just pattern-matching it.",
        "CA", "binary_invariant",
    ),
    make_record(
        "What operator patterns are universal across all languages?",
        "Arithmetic: + (0x2B) - (0x2D) * (0x2A) / (0x2F) — same bytes in every language. Comparison: < > == != — same or near-identical. Assignment: = — universal. Logical: && || ! or 'and' 'or' 'not' — varies in syntax but not in semantics. Bitwise: & | ^ ~ << >> — identical bytes, identical meaning in every language. These operators ARE the computation alphabet. There are only ~30 operator byte sequences and they mean the same thing everywhere.",
        "CA", "binary_invariant",
    ),
    # ── Invariant 6: Comment Patterns ──
    make_record(
        "How do comments work at the byte level?",
        "Comments are 'ignore everything until X' signals: // (0x2F 0x2F) in C/Java/Go/Rust/JS = ignore until newline. # (0x23) in Python/Ruby/Bash = same. /* */ (0x2F 0x2A ... 0x2A 0x2F) in C/Java/JS = ignore between markers. The parser sees the comment start bytes and SKIPS all bytes until the comment end. Comments are invisible to the AST — they produce zero nodes. But to the model, comments carry SEMANTIC information (intent, explanation) that the code itself doesn't encode.",
        "CA", "binary_invariant", ["CA", "DR"],
    ),
    # ── Invariant 7: Number Encoding ──
    make_record(
        "How are numbers represented at the byte level in code?",
        "Digit bytes 0x30-0x39 (ASCII '0'-'9') are universal. The parser reads consecutive digit bytes and converts to numeric value. 0x31 0x32 0x33 = '123' = numeric 123. Prefix 0x (0x30 0x78) = hexadecimal. Prefix 0b (0x30 0x62) = binary. Prefix 0o (0x30 0x6F) = octal. Decimal point 0x2E = float. Underscore 0x5F = visual separator (1_000_000). These prefix conventions are identical in Python, Rust, Go, JavaScript, Java, C. The bytes ARE the number system.",
        "CA", "binary_invariant",
    ),
    # ── Invariant 8: Keyword vs Identifier ──
    make_record(
        "How does the parser distinguish keywords from identifiers at the byte level?",
        "Keywords and identifiers use the SAME bytes (letters a-z, A-Z, digits 0-9, underscore _). The difference is a lookup table: the tokenizer reads letter bytes until it hits a non-letter byte, then checks: is 'def' in the keyword set? If yes = keyword token. If no = identifier token. Python has 35 keywords, JavaScript ~63, Rust ~51, Go 25. The parser cannot tell 'def' from 'dog' by bytes alone — it needs the keyword table. This is why reserved words exist: they're ordinary letter sequences with special parser meaning.",
        "CA", "binary_invariant", ["CA", "DR"],
    ),
    # ── Invariant 9: Newline as Statement Boundary ──
    make_record(
        "What role does the newline byte play in code parsing?",
        "Newline 0x0A (or 0x0D 0x0A on Windows) is the most overloaded byte in code. In Python/Go: statement terminator (like ; in other languages). In C/Java/Rust: ignored (whitespace). In preprocessor directives (#include): command terminator. In string literals: literal character. Same byte, four different meanings depending on parse context. The model must track which context it's in to know if 0x0A means 'end statement' or 'nothing'.",
        "CA", "binary_invariant",
    ),
    # ── Invariant 10: Import/Include Pattern ──
    make_record(
        "What is the universal pattern for module imports at the byte level?",
        "Every language has a 'load external code' keyword at the start of files: Python 'import'/'from', JavaScript 'import'/'require', Rust 'use', Go 'import', C '#include', Java 'import'. The pattern is always: keyword + module path + optional alias. At the byte level, these are the first non-comment, non-whitespace bytes in a file. The parser treats them specially: they modify the symbol table before any code runs. Import position (top of file) is a universal convention enforced by most linters but only required by some parsers.",
        "CA", "binary_invariant", ["CA", "AV"],
    ),
    # ── Invariant 11: Scope and Block Structure ──
    make_record(
        "How is scope encoded at the byte level across languages?",
        "Two universal scope mechanisms: (1) Braces { } — C, Java, JavaScript, Rust, Go. Bytes 0x7B and 0x7D create explicit scope boundaries. (2) Indentation — Python. Sequences of 0x20 (space) bytes at line start. Both encode the SAME abstract concept: 'this code belongs to this block.' The parser builds identical tree structures from both — just different byte-level signals. A universal code model must handle both: brace-counting AND indent-measuring. They're isomorphic at the AST level.",
        "DR", "binary_invariant", ["CA", "DR"],
    ),
    # ── Invariant 12: EOF and File Structure ──
    make_record(
        "What is the universal file structure of source code at the byte level?",
        "Every source file follows the same macro structure: (1) Optional BOM/shebang (first 2-4 bytes), (2) Imports/includes (module loading), (3) Declarations (types, constants, globals), (4) Definitions (functions, classes, methods), (5) Optional entry point (main). At the byte level, the file is just a sequence of 0x09-0x7E bytes plus newlines. But the ORDER of those bytes encodes a dependency graph: imports before use, declarations before references, definitions before calls. That ordering is a universal invariant — violating it is always an error.",
        "DR", "binary_invariant", ["CA", "DR"],
    ),
    # ── Byte-to-Token-to-AST Pipeline ──
    make_record(
        "What bytes does Python's parser see when it encounters 'def add(a, b):'?",
        "The parser receives bytes: 0x64 0x65 0x66 0x20 0x61 0x64 0x64 0x28 0x61 0x2C 0x20 0x62 0x29 0x3A. The tokenizer splits: NAME('def'), NAME('add'), OP('('), NAME('a'), OP(','), NAME('b'), OP(')'), OP(':'). The parser builds AST: FunctionDef(name='add', args=arguments(args=[arg(arg='a'), arg(arg='b')])). Every level — bytes to tokens to AST — is deterministic and reversible. The model that knows all three levels understands code structurally, not just as text patterns.",
        "CA", "bytes_to_ast",
    ),
    make_record(
        "How does 'x = 1 + 2' look at bytes, tokens, and AST levels?",
        "Bytes: 0x78 0x20 0x3D 0x20 0x31 0x20 0x2B 0x20 0x32. Tokens: NAME('x'), OP('='), NUMBER('1'), OP('+'), NUMBER('2'). AST: Assign(targets=[Name(id='x')], value=BinOp(left=Constant(value=1), op=Add(), right=Constant(value=2))). The bytes are 9 characters. The tokens are 5 meaningful units. The AST is a tree with 7 nodes. Each level compresses: 9 bytes -> 5 tokens -> 1 semantic operation (assign sum to variable). The model that knows all levels can predict at the right abstraction.",
        "CA", "bytes_to_ast",
    ),
    make_record(
        "What is the difference between '=' and '==' at bytes, tokens, and AST levels?",
        "Bytes: = is 0x3D (1 byte). == is 0x3D 0x3D (2 bytes). One extra byte changes everything. Tokens: = becomes OP('=') which is ASSIGNMENT. == becomes OP('==') which is COMPARISON. AST: = creates an Assign node (write to memory). == creates a Compare node (read and test). The consequences: 'x = 5' changes program state. 'x == 5' reads program state. This is the most common bug in programming (using = when you meant ==). The byte-level difference is exactly 1 byte. The semantic difference is total.",
        "CA", "bytes_to_ast",
    ),
    # ── Cross-Language Universal Patterns ──
    make_record(
        "What function definition looks like at the byte level across 5 languages?",
        "Python: 0x64,0x65,0x66,0x20 ('def '). JavaScript: 0x66,0x75,0x6E,0x63,0x74,0x69,0x6F,0x6E,0x20 ('function '). Rust: 0x66,0x6E,0x20 ('fn '). Go: 0x66,0x75,0x6E,0x63,0x20 ('func '). C: no keyword — type + name + parens. Five different byte sequences, one identical semantic meaning: 'define a callable block.' The AST node is equivalent in all cases: FunctionDef(name, args, body). The model that knows all five byte patterns can translate between languages because it understands the shared AST.",
        "DR", "cross_language", ["CA", "DR"],
    ),
    make_record(
        "What conditional statement looks like at the byte level across languages?",
        "All languages use 'if' (0x69,0x66) as the conditional keyword — Python, JavaScript, Rust, Go, C, Java, Ruby, Swift. This is the most universal keyword in programming: two bytes, identical in every language. The structure after 'if' varies: Python uses colon + indent, C/Java/Rust use parentheses + braces. But the AST is identical: If(test=condition, body=block, orelse=optional_block). Two bytes trigger the most common control flow structure in all of computing.",
        "CA", "cross_language", ["CA", "DR"],
    ),
    make_record(
        "What loop constructs share at the byte level?",
        "Two universal loop keywords: 'for' (0x66,0x6F,0x72) and 'while' (0x77,0x68,0x69,0x6C,0x65). Present in Python, JavaScript, Rust, Go, C, Java, Ruby. 'for' iterates over a sequence or range. 'while' repeats until a condition is false. At AST level: For(target, iter, body) and While(test, body). The bytes differ slightly across languages (Rust uses 'loop' instead of 'while true') but the semantics are identical. Every Turing-complete language MUST have at least one loop construct — it's a mathematical necessity.",
        "CA", "cross_language", ["CA", "DR"],
    ),
    # ── Tongue-Specific Code Views ──
    make_record(
        "How does the CA tongue view code differently from the DR tongue?",
        "CA (Compute, w=4.236) sees code as: what does it DO? Input types, output types, algorithm complexity, runtime behavior. It cares about 0x2B (addition), 0x2A (multiplication), 0x3D (assignment) — the operators that transform data. DR (Structure, w=11.09) sees code as: WHY is it organized this way? Module boundaries, class hierarchies, import graphs, architectural patterns. It cares about 'class', 'def', 'import', 'module' — the keywords that define structure. Same code, two completely different readings. The model trained on both understands code as a multi-dimensional object.",
        "DR", "tongue_view", ["CA", "DR"],
    ),
    make_record(
        "How does the UM tongue view code?",
        "UM (Security, w=6.854) sees code as: what could go WRONG? It flags: user input flowing to eval() (code injection), string concatenation in SQL (injection), Math.random() in crypto (weak entropy), hardcoded credentials (exposure), unvalidated file paths (traversal). These are all byte patterns: 'eval(' = 0x65,0x76,0x61,0x6C,0x28 is a danger signal. 'os.system(' is another. UM doesn't care what the code computes — it cares what the code EXPOSES. That's why UM-null on a code record means 'no security surface' which is itself valuable training signal.",
        "UM", "tongue_view", ["UM", "CA"],
    ),
    make_record(
        "What does it mean when RU tongue is active on a code record?",
        "RU (Policy/Energy, w=2.618) views code as: what RULES does it follow? Linting rules, style guides, naming conventions, error handling patterns. RU-active on code means the code involves policy decisions: retry logic, rate limiting, circuit breakers, validation rules, permission checks. At the byte level, RU looks for: 'try'/'except'/'catch' (error policy), 'if err != nil' (Go error handling), 'assert' (contract enforcement). RU-null means the code has no policy logic — it's pure computation, which is also a signal.",
        "RU", "tongue_view", ["RU", "CA"],
    ),
    # ── Absence Patterns in Code ──
    make_record(
        "What does tongue absence tell you about code?",
        "When UM (security) is null: the code has no authentication, no encryption, no input validation — it's internal/trusted. When AV (I/O) is null: the code does no file reads, no network calls, no database queries — it's pure logic. When RU (policy) is null: no error handling, no retries, no validation — it's happy-path only. When KO (control) is null: no orchestration, no state machines, no workflow control — it's a leaf function. Each null tongue tells the model what NOT to think about, saving compute on irrelevant dimensions. Average code function has 4 null tongues.",
        "DR", "absence_pattern", ["DR", "CA"],
    ),
    make_record(
        "Why is the null pattern more informative than presence for code training?",
        "A function tagged CA-active tells you 'this computes something' — obvious. But CA-active with [KO,AV,RU,UM,DR]-null tells you: 'this is a pure computation with no control flow, no I/O, no policy, no security, and no structural complexity.' That's a MUCH stronger signal. The model learns: when I see this null pattern, I can skip 5 out of 6 processing channels. Standard code training gives presence only. Multi-view training gives presence AND structured absence. That's why it improves by 14% — the model learns when NOT to activate expensive channels.",
        "DR", "absence_pattern",
    ),
    # ── Binary-First Encoding Principles ──
    make_record(
        "What is the binary-first principle for code understanding?",
        "Binary-first means: know the bytes before the words, know the words before the syntax, know the syntax before the semantics. L0: bytes 0x64,0x65,0x66 exist. L1: those bytes spell 'def', a Python keyword. L2: 'def' creates a function definition scope. L3: 'def add(a, b): return a + b' implements addition. A model trained bottom-up understands WHY 'def' works (it's three specific bytes the parser looks for) rather than just pattern-matching it. This substrate knowledge prevents hallucinated syntax — the model knows what bytes are valid.",
        "DR", "principle", ["CA", "DR"],
    ),
    make_record(
        "How does the binary-first stack map to SCBE layers for code?",
        "L0 = bytes (0x00-0xFF) mapped to CA tongue — what the machine literally sees. L1 = tokens (keywords, identifiers, operators, literals) mapped to CA+DR — structure emerges from byte sequences. L2 = patterns (function templates, class hierarchies, import graphs) mapped to DR+KO — architectural intent and control flow. L3 = programs (working code that solves problems) mapped to ALL tongues — full meaning requires all dimensions. Each layer compresses: billions of byte sequences reduce to thousands of valid programs. The compression ratio IS the structure.",
        "DR", "principle", ["CA", "DR", "KO"],
    ),
    # ── Type System as Byte Constraint ──
    make_record(
        "How do type systems constrain byte sequences?",
        "Without types, 'x + y' could mean anything: number addition, string concatenation, list merge. Types constrain: if x: int and y: int, then + MUST mean numeric addition (bytes 0x2B). The type system eliminates ambiguous byte interpretations. Static types (Rust, Go, Java) resolve at compile time — before bytes execute. Dynamic types (Python, JavaScript) resolve at runtime — bytes execute and type is checked live. Type annotations in code are metadata bytes that constrain how other bytes are interpreted. The model that understands types can predict operator behavior from context.",
        "DR", "type_system", ["CA", "DR"],
    ),
    # ── Error as Signal ──
    make_record(
        "What do syntax errors look like at the byte level?",
        "Every syntax error is a byte that violates a parser expectation: missing 0x29 ')' after 0x28 '(' = unmatched delimiter. 0x3D '=' where 0x3D 0x3D '==' was expected = assignment in condition. 0x09 (tab) mixed with 0x20 (space) in Python = IndentationError. Unexpected 0x7D '}' = extra closing brace. The parser has a state machine: at each byte, it expects a set of valid next bytes. Syntax error = the actual byte is not in the expected set. This is why code has clear right/wrong — it's deterministic byte validation.",
        "CA", "error_signal", ["CA", "RU"],
    ),
]


def generate():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()

    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        for record in RECORDS:
            record["timestamp"] = timestamp
            f.write(json.dumps(record, ensure_ascii=True) + "\n")

    print(f"Generated {len(RECORDS)} code substrate L0 records")
    print(f"Output: {OUTPUT}")

    # Stats
    categories = {}
    tongues = {}
    for r in RECORDS:
        cat = r["category"]
        categories[cat] = categories.get(cat, 0) + 1
        t = r["tongue"]
        tongues[t] = tongues.get(t, 0) + 1

    print(f"\nBy category:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    print(f"\nBy dominant tongue:")
    for t, count in sorted(tongues.items(), key=lambda x: -x[1]):
        print(f"  {t}: {count}")

    avg_null = sum(len(r["tongues_null"]) for r in RECORDS) / len(RECORDS)
    print(f"\nAvg null tongues per record: {avg_null:.1f}")


if __name__ == "__main__":
    generate()
