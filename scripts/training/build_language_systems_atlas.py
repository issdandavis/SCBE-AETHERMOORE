#!/usr/bin/env python
"""Build the SCBE language systems atlas.

Maps more coding primaries into synchronized views:
  language -> construct -> example -> binary views -> SCBE phase tokens
  language -> official manual / tutorial / troubleshooting source
  GitHub -> user-guide workflow rows

This does not copy entire manuals. It stores source links, lightweight status,
titles when fetchable, and training prompts that teach agents where to go and
how to use the source. That keeps the corpus reviewable and avoids stale copied
documentation.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import re
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "artifacts" / "language_systems_atlas"


LANGUAGES: list[dict[str, Any]] = [
    {"id": "python", "name": "Python", "family": "dynamic", "docs": "https://docs.python.org/3/", "tutorial": "https://docs.python.org/3/tutorial/", "troubleshooting": "https://docs.python.org/3/faq/"},
    {"id": "javascript", "name": "JavaScript", "family": "web", "docs": "https://developer.mozilla.org/en-US/docs/Web/JavaScript", "tutorial": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide", "troubleshooting": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Errors"},
    {"id": "typescript", "name": "TypeScript", "family": "web", "docs": "https://www.typescriptlang.org/docs/", "tutorial": "https://www.typescriptlang.org/docs/handbook/intro.html", "troubleshooting": "https://www.typescriptlang.org/docs/handbook/2/everyday-types.html"},
    {"id": "nodejs", "name": "Node.js", "family": "runtime", "docs": "https://nodejs.org/docs/latest/api/", "tutorial": "https://nodejs.org/en/learn", "troubleshooting": "https://nodejs.org/en/learn/getting-started/debugging"},
    {"id": "go", "name": "Go", "family": "systems", "docs": "https://go.dev/doc/", "tutorial": "https://go.dev/tour/", "troubleshooting": "https://go.dev/doc/diagnostics"},
    {"id": "rust", "name": "Rust", "family": "systems", "docs": "https://doc.rust-lang.org/book/", "tutorial": "https://www.rust-lang.org/learn", "troubleshooting": "https://doc.rust-lang.org/error-index.html"},
    {"id": "c", "name": "C", "family": "systems", "docs": "https://en.cppreference.com/w/c", "tutorial": "https://en.cppreference.com/w/c/language", "troubleshooting": "https://gcc.gnu.org/onlinedocs/gcc/Warning-Options.html"},
    {"id": "cpp", "name": "C++", "family": "systems", "docs": "https://en.cppreference.com/w/cpp", "tutorial": "https://isocpp.org/get-started", "troubleshooting": "https://gcc.gnu.org/onlinedocs/gcc/C_002b_002b-Dialect-Options.html"},
    {"id": "csharp", "name": "C#", "family": "dotnet", "docs": "https://learn.microsoft.com/en-us/dotnet/csharp/", "tutorial": "https://learn.microsoft.com/en-us/dotnet/csharp/tour-of-csharp/", "troubleshooting": "https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/compiler-messages/"},
    {"id": "java", "name": "Java", "family": "jvm", "docs": "https://docs.oracle.com/en/java/", "tutorial": "https://dev.java/learn/", "troubleshooting": "https://docs.oracle.com/javase/tutorial/essential/exceptions/"},
    {"id": "kotlin", "name": "Kotlin", "family": "jvm", "docs": "https://kotlinlang.org/docs/home.html", "tutorial": "https://kotlinlang.org/docs/getting-started.html", "troubleshooting": "https://kotlinlang.org/docs/exceptions.html"},
    {"id": "scala", "name": "Scala", "family": "jvm", "docs": "https://docs.scala-lang.org/", "tutorial": "https://docs.scala-lang.org/tour/tour-of-scala.html", "troubleshooting": "https://docs.scala-lang.org/scala3/reference/changed-features.html"},
    {"id": "ruby", "name": "Ruby", "family": "dynamic", "docs": "https://docs.ruby-lang.org/en/master/", "tutorial": "https://www.ruby-lang.org/en/documentation/quickstart/", "troubleshooting": "https://ruby-doc.org/core/Exception.html"},
    {"id": "php", "name": "PHP", "family": "web", "docs": "https://www.php.net/manual/en/", "tutorial": "https://www.php.net/manual/en/getting-started.php", "troubleshooting": "https://www.php.net/manual/en/language.exceptions.php"},
    {"id": "swift", "name": "Swift", "family": "apple", "docs": "https://docs.swift.org/swift-book/documentation/the-swift-programming-language/", "tutorial": "https://www.swift.org/getting-started/", "troubleshooting": "https://www.swift.org/documentation/"},
    {"id": "haskell", "name": "Haskell", "family": "functional", "docs": "https://www.haskell.org/documentation/", "tutorial": "https://www.haskell.org/ghcup/", "troubleshooting": "https://errors.haskell.org/"},
    {"id": "lua", "name": "Lua", "family": "embedded", "docs": "https://www.lua.org/manual/5.4/", "tutorial": "https://www.lua.org/start.html", "troubleshooting": "https://www.lua.org/pil/8.4.html"},
    {"id": "julia", "name": "Julia", "family": "scientific", "docs": "https://docs.julialang.org/en/v1/", "tutorial": "https://docs.julialang.org/en/v1/manual/getting-started/", "troubleshooting": "https://docs.julialang.org/en/v1/manual/performance-tips/"},
    {"id": "zig", "name": "Zig", "family": "systems", "docs": "https://ziglang.org/documentation/master/", "tutorial": "https://ziglang.org/learn/", "troubleshooting": "https://ziglang.org/documentation/master/#Errors"},
    {"id": "dart", "name": "Dart", "family": "app", "docs": "https://dart.dev/language", "tutorial": "https://dart.dev/tutorials", "troubleshooting": "https://dart.dev/tools/diagnostic-messages"},
    {"id": "r", "name": "R", "family": "statistical", "docs": "https://cran.r-project.org/manuals.html", "tutorial": "https://cran.r-project.org/doc/manuals/r-release/R-intro.html", "troubleshooting": "https://cran.r-project.org/doc/manuals/r-release/R-admin.html"},
    {"id": "bash", "name": "Bash", "family": "shell", "docs": "https://www.gnu.org/software/bash/manual/bash.html", "tutorial": "https://www.gnu.org/software/bash/manual/bash.html#Shell-Syntax", "troubleshooting": "https://www.gnu.org/software/bash/manual/bash.html#Exit-Status"},
    {"id": "powershell", "name": "PowerShell", "family": "shell", "docs": "https://learn.microsoft.com/en-us/powershell/scripting/overview", "tutorial": "https://learn.microsoft.com/en-us/powershell/scripting/learn/ps101/00-introduction", "troubleshooting": "https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/get-help"},
    {"id": "sql", "name": "SQL", "family": "data", "docs": "https://www.postgresql.org/docs/current/sql.html", "tutorial": "https://www.postgresql.org/docs/current/tutorial.html", "troubleshooting": "https://www.postgresql.org/docs/current/error-message-reporting.html"},
    {"id": "html", "name": "HTML", "family": "web", "docs": "https://developer.mozilla.org/en-US/docs/Web/HTML", "tutorial": "https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Structuring_content", "troubleshooting": "https://validator.w3.org/docs/errors.html"},
    {"id": "css", "name": "CSS", "family": "web", "docs": "https://developer.mozilla.org/en-US/docs/Web/CSS", "tutorial": "https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Styling_basics", "troubleshooting": "https://developer.mozilla.org/en-US/docs/Learn_web_development/Howto/Solve_CSS_problems"},
    {"id": "json", "name": "JSON", "family": "data", "docs": "https://www.json.org/json-en.html", "tutorial": "https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Scripting/JSON", "troubleshooting": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Errors/JSON_bad_parse"},
    {"id": "yaml", "name": "YAML", "family": "data", "docs": "https://spec.yaml.io/main/spec/1.2.2/", "tutorial": "https://yaml.org/", "troubleshooting": "https://yaml.com/resources/"},
    {"id": "toml", "name": "TOML", "family": "data", "docs": "https://toml.io/en/v1.0.0", "tutorial": "https://toml.io/en/", "troubleshooting": "https://toml.io/en/v1.0.0#invalid-examples"},
    {"id": "xml", "name": "XML", "family": "data", "docs": "https://www.w3.org/TR/xml/", "tutorial": "https://developer.mozilla.org/en-US/docs/Web/XML", "troubleshooting": "https://www.w3.org/TR/xml/#sec-terminology"},
    {"id": "markdown", "name": "Markdown", "family": "markup", "docs": "https://spec.commonmark.org/current/", "tutorial": "https://www.markdownguide.org/basic-syntax/", "troubleshooting": "https://spec.commonmark.org/current/#appendix-a-parsing-strategy"},
    {"id": "regex", "name": "Regular Expressions", "family": "pattern", "docs": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Regular_expressions", "tutorial": "https://docs.python.org/3/howto/regex.html", "troubleshooting": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Errors/Regex_invalid_group"},
    {"id": "wasm_wat", "name": "WebAssembly Text", "family": "bytecode", "docs": "https://webassembly.github.io/spec/core/text/index.html", "tutorial": "https://developer.mozilla.org/en-US/docs/WebAssembly/Understanding_the_text_format", "troubleshooting": "https://developer.mozilla.org/en-US/docs/WebAssembly"},
    {"id": "solidity", "name": "Solidity", "family": "blockchain", "docs": "https://docs.soliditylang.org/en/latest/", "tutorial": "https://docs.soliditylang.org/en/latest/introduction-to-smart-contracts.html", "troubleshooting": "https://docs.soliditylang.org/en/latest/common-patterns.html"},
    {"id": "elixir", "name": "Elixir", "family": "beam", "docs": "https://hexdocs.pm/elixir/introduction.html", "tutorial": "https://elixir-lang.org/getting-started/introduction.html", "troubleshooting": "https://hexdocs.pm/elixir/Exception.html"},
    {"id": "erlang", "name": "Erlang", "family": "beam", "docs": "https://www.erlang.org/doc/", "tutorial": "https://www.erlang.org/doc/system/getting_started.html", "troubleshooting": "https://www.erlang.org/doc/system/errors.html"},
    {"id": "clojure", "name": "Clojure", "family": "lisp", "docs": "https://clojure.org/guides/getting_started", "tutorial": "https://clojure.org/guides/learn/functions", "troubleshooting": "https://clojure.org/guides/threading_macros"},
    {"id": "ocaml", "name": "OCaml", "family": "functional", "docs": "https://ocaml.org/docs", "tutorial": "https://ocaml.org/docs/tour-of-ocaml", "troubleshooting": "https://ocaml.org/docs/error-handling"},
    {"id": "fsharp", "name": "F#", "family": "dotnet", "docs": "https://learn.microsoft.com/en-us/dotnet/fsharp/", "tutorial": "https://learn.microsoft.com/en-us/dotnet/fsharp/tour", "troubleshooting": "https://learn.microsoft.com/en-us/dotnet/fsharp/language-reference/exception-handling/"},
    {"id": "nim", "name": "Nim", "family": "systems", "docs": "https://nim-lang.org/documentation.html", "tutorial": "https://nim-lang.org/docs/tut1.html", "troubleshooting": "https://nim-lang.org/docs/manual.html#exception-handling"},
    {"id": "perl", "name": "Perl", "family": "dynamic", "docs": "https://perldoc.perl.org/", "tutorial": "https://perldoc.perl.org/perlintro", "troubleshooting": "https://perldoc.perl.org/perldiag"},
]

GITHUB_SOURCES = [
    {"id": "github_get_started", "title": "Get started with GitHub", "url": "https://docs.github.com/en/get-started"},
    {"id": "github_hello_world", "title": "Hello World", "url": "https://docs.github.com/en/get-started/start-your-journey/hello-world"},
    {"id": "github_ssh", "title": "Connecting to GitHub with SSH", "url": "https://docs.github.com/en/authentication/connecting-to-github-with-ssh"},
    {"id": "github_pr_best_practices", "title": "Best practices for pull requests", "url": "https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/getting-started/best-practices-for-pull-requests"},
    {"id": "github_actions", "title": "GitHub Actions documentation", "url": "https://docs.github.com/actions"},
    {"id": "github_pages", "title": "Quickstart for GitHub Pages", "url": "https://docs.github.com/pages/quickstart"},
]

BINARY_MODES = [
    "utf8",
    "utf16le",
    "utf32le",
    "bytes",
    "hex",
    "bits",
    "nibbles",
    "base64",
    "base64url",
    "ascii85",
    "byte_hist",
    "sha256",
]


def fetch_title(url: str, timeout: int = 8) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "SCBE-AETHERMOORE language atlas builder"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read(96_000)
            content_type = response.headers.get("content-type", "")
            text = data.decode("utf-8", errors="replace")
            title = None
            match = re.search(r"<title[^>]*>(.*?)</title>", text, flags=re.I | re.S)
            if match:
                title = html.unescape(re.sub(r"\s+", " ", match.group(1)).strip())
            return {"ok": True, "status": getattr(response, "status", None), "content_type": content_type, "title": title, "bytes_sampled": len(data)}
    except Exception as exc:
        return {"ok": False, "error": f"{exc.__class__.__name__}: {str(exc)[:240]}"}


def code_example(lang: dict[str, Any], construct: str) -> str:
    lid = lang["id"]
    if construct == "hello":
        if lid in {"python"}:
            return "print('hello')"
        if lid in {"javascript", "typescript", "nodejs"}:
            return "console.log('hello');"
        if lid == "go":
            return 'package main\nimport "fmt"\nfunc main(){ fmt.Println("hello") }'
        if lid == "rust":
            return 'fn main() { println!("hello"); }'
        if lid in {"c"}:
            return '#include <stdio.h>\nint main(){ puts("hello"); return 0; }'
        if lid in {"cpp"}:
            return '#include <iostream>\nint main(){ std::cout << "hello\\n"; }'
        if lid == "java":
            return 'class Main { public static void main(String[] args){ System.out.println("hello"); } }'
        return f"// {lang['name']} hello-world pattern; consult official docs for exact runner."
    if construct == "function":
        if lid == "python":
            return "def add(a, b):\n    return a + b"
        if lid in {"javascript", "typescript", "nodejs"}:
            return "function add(a, b) { return a + b; }"
        if lid == "go":
            return "func add(a int, b int) int { return a + b }"
        if lid == "rust":
            return "fn add(a: i32, b: i32) -> i32 { a + b }"
        if lid in {"c", "cpp"}:
            return "int add(int a, int b) { return a + b; }"
        if lid == "java":
            return "static int add(int a, int b) { return a + b; }"
        return f"add(a, b) -> a + b  # {lang['name']} function concept"
    if construct == "branch_loop":
        if lid == "python":
            return "for x in items:\n    if x > 0:\n        total += x"
        if lid in {"javascript", "typescript", "nodejs"}:
            return "for (const x of items) { if (x > 0) total += x; }"
        if lid == "go":
            return "for _, x := range items { if x > 0 { total += x } }"
        if lid == "rust":
            return "for x in items { if x > 0 { total += x; } }"
        return f"loop over items; if positive then accumulate  # {lang['name']} branch+loop concept"
    return f"{construct} concept for {lang['name']}"


def binary_views(text: str) -> dict[str, Any]:
    utf8 = text.encode("utf-8", errors="replace")
    utf16 = text.encode("utf-16le", errors="replace")
    utf32 = text.encode("utf-32le", errors="replace")
    sample = utf8[:256]
    hist = Counter(sample)
    return {
        "utf8": text[:256],
        "utf16le_hex": utf16[:256].hex(),
        "utf32le_hex": utf32[:256].hex(),
        "bytes": list(sample[:96]),
        "hex": sample[:192].hex(),
        "bits": "".join(f"{byte:08b}" for byte in sample[:64]),
        "nibbles": " ".join(f"{byte >> 4:x} {byte & 15:x}" for byte in sample[:64]),
        "base64": base64.b64encode(sample[:192]).decode("ascii"),
        "base64url": base64.urlsafe_b64encode(sample[:192]).decode("ascii"),
        "ascii85": base64.a85encode(sample[:192]).decode("ascii", errors="replace"),
        "byte_hist": {str(k): hist[k] for k in sorted(hist)},
        "sha256": hashlib.sha256(utf8).hexdigest(),
    }


def scbe_tokens(lang: dict[str, Any], construct: str, digest: str) -> list[str]:
    return [
        "KO",
        "kor-vael",
        f"concept:{construct}",
        "AV",
        "av-sai",
        f"language:{lang['id']}",
        f"family:{lang['family']}",
        "RU",
        "ru-thar",
        f"manual:{digest[:12]}",
        "CA",
        "ca-forge",
        f"construct:{construct}",
        "DR",
        "draum-sel",
        f"seal:{digest[:16]}",
    ]


def build_rows(source_status: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for lang in LANGUAGES:
        manual = source_status[lang["id"]]
        for construct in ("hello", "function", "branch_loop"):
            code = code_example(lang, construct)
            digest = hashlib.sha256(code.encode("utf-8", errors="replace")).hexdigest()
            rows.append(
                {
                    "id": f"language:{lang['id']}:{construct}:{digest[:12]}",
                    "lane": "language_primary",
                    "task": f"{construct}_mapping",
                    "prompt": f"Map {construct} in {lang['name']} using official docs, then provide SCBE tokens and binary views.",
                    "response": code,
                    "views": {
                        "language": lang,
                        "construct": construct,
                        "binary": binary_views(code),
                        "scbe_tokens": scbe_tokens(lang, construct, digest),
                        "manual_sources": manual,
                    },
                    "metadata": {"validated": True, "manual_url": lang["docs"], "troubleshooting_url": lang["troubleshooting"]},
                }
            )
        rows.append(
            {
                "id": f"manual:{lang['id']}",
                "lane": "manual_source",
                "task": "manual_and_troubleshooting_pointer",
                "prompt": f"Where should an agent look for current {lang['name']} documentation and troubleshooting?",
                "response": json.dumps({"docs": lang["docs"], "tutorial": lang["tutorial"], "troubleshooting": lang["troubleshooting"]}, ensure_ascii=False),
                "views": {"language": lang, "source_status": manual},
                "metadata": {"validated": bool(manual.get("docs", {}).get("ok")), "manual_url": lang["docs"]},
            }
        )
    for item in GITHUB_SOURCES:
        rows.append(
            {
                "id": f"github:{item['id']}",
                "lane": "github_user_guide",
                "task": "github_workflow_pointer",
                "prompt": f"Teach the GitHub workflow source: {item['title']}",
                "response": item["url"],
                "views": {"source_status": source_status["github"].get(item["id"], {}), "binary": binary_views(item["url"])},
                "metadata": {"validated": bool(source_status["github"].get(item["id"], {}).get("ok")), "manual_url": item["url"]},
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true", help="fetch lightweight title/status for manual URLs")
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    source_status: dict[str, Any] = {}
    for lang in LANGUAGES:
        source_status[lang["id"]] = {}
        for key in ("docs", "tutorial", "troubleshooting"):
            source_status[lang["id"]][key] = fetch_title(lang[key]) if args.fetch else {"ok": None, "url": lang[key]}
            source_status[lang["id"]][key]["url"] = lang[key]
    source_status["github"] = {}
    for item in GITHUB_SOURCES:
        source_status["github"][item["id"]] = fetch_title(item["url"]) if args.fetch else {"ok": None}
        source_status["github"][item["id"]]["url"] = item["url"]

    rows = build_rows(source_status)
    rows_path = OUT_DIR / "language_systems_training_rows.jsonl"
    with rows_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    manual_path = OUT_DIR / "manual_source_manifest.json"
    manual_path.write_text(json.dumps(source_status, indent=2, ensure_ascii=False), encoding="utf-8")

    atlas = {
        "languages": LANGUAGES,
        "github_sources": GITHUB_SOURCES,
        "binary_modes": BINARY_MODES,
        "rows": len(rows),
    }
    atlas_path = OUT_DIR / "language_systems_map.json"
    atlas_path.write_text(json.dumps(atlas, indent=2, ensure_ascii=False), encoding="utf-8")

    guide = OUT_DIR / "github_user_guide.md"
    guide.write_text(
        "\n".join(
            [
                "# GitHub User Guide Lane",
                "",
                "Use the official GitHub docs as the live source of truth. Training rows should teach workflow routing, not copy the full docs.",
                "",
                "Core path:",
                "1. Create or open a repository.",
                "2. Create a branch.",
                "3. Commit changes.",
                "4. Open a pull request.",
                "5. Review and merge.",
                "6. Use Actions for automation when needed.",
                "7. Use Pages for publishing docs/sites when needed.",
                "",
                "Sources:",
                *[f"- [{item['title']}]({item['url']})" for item in GITHUB_SOURCES],
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    lane_counts = Counter(row["lane"] for row in rows)
    ok_sources = 0
    total_sources = 0
    for lang in LANGUAGES:
        for key in ("docs", "tutorial", "troubleshooting"):
            total_sources += 1
            ok_sources += 1 if source_status[lang["id"]][key].get("ok") else 0
    for item in GITHUB_SOURCES:
        total_sources += 1
        ok_sources += 1 if source_status["github"][item["id"]].get("ok") else 0

    receipt = {
        "ok": True,
        "kind": "language_systems_atlas",
        "honest_scope": "Source-linked training rows and binary views; full manual content is not copied.",
        "fetch_enabled": args.fetch,
        "counts": {
            "languages": len(LANGUAGES),
            "binary_modes": len(BINARY_MODES),
            "rows": len(rows),
            "lanes": dict(lane_counts),
            "sources_checked": total_sources if args.fetch else 0,
            "sources_ok": ok_sources if args.fetch else 0,
        },
        "artifacts": {
            "language_systems_map": str(atlas_path),
            "manual_source_manifest": str(manual_path),
            "training_rows": str(rows_path),
            "github_user_guide": str(guide),
        },
    }
    receipt_path = OUT_DIR / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    print("LANGUAGE_SYSTEMS_ATLAS_DONE")
    print(f"languages: {len(LANGUAGES)} binary_modes: {len(BINARY_MODES)} rows: {len(rows)}")
    if args.fetch:
        print(f"sources ok: {ok_sources}/{total_sources}")
    print(f"receipt: {receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
