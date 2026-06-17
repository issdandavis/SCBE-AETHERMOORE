// ast_cube_poly — polyglot tree-sitter AST cube encoder + syntax validator.
//
// One uniform walk, N grammars: every language parses to the same cube-matrix
// [type_id(kind), depth, 6 faces, 6 splitmix location], and `--check` reports
// whether a source file is syntactically valid (tree-sitter has_error) — the
// validator for polyglot.py's emitted faces ("compiles no matter what").

use tree_sitter::{Language, Node, Parser};

const GOLDEN: u64 = 0x9E37_79B1;

fn language_for(name: &str) -> Option<Language> {
    Some(match name {
        "js" | "javascript" | "jsx" => tree_sitter_javascript::LANGUAGE.into(),
        "ts" | "typescript" => tree_sitter_typescript::LANGUAGE_TYPESCRIPT.into(),
        "tsx" => tree_sitter_typescript::LANGUAGE_TSX.into(),
        "python" | "py" => tree_sitter_python::LANGUAGE.into(),
        "c" | "h" => tree_sitter_c::LANGUAGE.into(),
        "cpp" | "cc" | "cxx" | "hpp" => tree_sitter_cpp::LANGUAGE.into(),
        "csharp" | "cs" => tree_sitter_c_sharp::LANGUAGE.into(),
        "go" => tree_sitter_go::LANGUAGE.into(),
        "rust" | "rs" => tree_sitter_rust::LANGUAGE.into(),
        "java" => tree_sitter_java::LANGUAGE.into(),
        "ruby" | "rb" => tree_sitter_ruby::LANGUAGE.into(),
        "php" => tree_sitter_php::LANGUAGE_PHP.into(),
        "julia" | "jl" => tree_sitter_julia::LANGUAGE.into(),
        "haskell" | "hs" => tree_sitter_haskell::LANGUAGE.into(),
        "scala" => tree_sitter_scala::LANGUAGE.into(),
        "lua" => tree_sitter_lua::LANGUAGE.into(),
        "swift" => tree_sitter_swift::LANGUAGE.into(),
        "zig" => tree_sitter_zig::LANGUAGE.into(),
        "kotlin" | "kt" => tree_sitter_kotlin_ng::LANGUAGE.into(),
        _ => return None,
    })
}

const GRAMMARS: &[&str] = &[
    "javascript", "typescript", "tsx", "python", "c", "cpp", "csharp", "go", "rust",
    "java", "ruby", "php", "julia", "haskell", "scala", "lua", "swift", "zig", "kotlin",
];

fn lang_for_ext(ext: &str) -> Option<&'static str> {
    Some(match ext {
        "js" | "jsx" | "mjs" | "cjs" => "javascript",
        "ts" => "typescript",
        "tsx" => "tsx",
        "py" | "pyi" => "python",
        "c" | "h" => "c",
        "cc" | "cpp" | "cxx" | "hpp" | "hxx" => "cpp",
        "cs" => "csharp",
        "go" => "go",
        "rs" => "rust",
        "java" => "java",
        "rb" => "ruby",
        "php" => "php",
        "jl" => "julia",
        "hs" => "haskell",
        "scala" | "sc" => "scala",
        "lua" => "lua",
        "swift" => "swift",
        "zig" => "zig",
        "kt" | "kts" => "kotlin",
        _ => return None,
    })
}

#[inline]
fn faces(kind: &str) -> [i64; 6] {
    let has = |ns: &[&str]| ns.iter().any(|n| kind.contains(n));
    let mut f = [0i64; 6];
    if has(&["if", "for", "while", "switch", "case", "return", "break", "continue",
             "loop", "ternary", "conditional", "match", "yield", "goto", "when_"]) { f[0] = 1; }
    if has(&["call", "import", "include", "require", "argument", "parameter",
             "await", "export", "print", "using"]) { f[1] = 1; }
    if has(&["function", "method", "class", "module", "namespace", "struct", "impl",
             "trait", "interface", "enum", "block", "lambda", "closure", "program",
             "package", "definition", "declaration_list", "source_file"]) { f[2] = 1; }
    if has(&["binary", "unary", "number", "integer", "float", "comparison",
             "arithmetic", "subscript", "index", "boolean", "operator", "bitwise"]) { f[3] = 1; }
    if has(&["try", "catch", "throw", "raise", "assert", "unsafe", "delete",
             "except", "finally", "panic", "defer", "recover"]) { f[4] = 1; }
    if has(&["assign", "declaration", "array", "list", "object", "dictionary",
             "map", "tuple", "string", "template", "literal", "spread", "field"]) { f[5] = 1; }
    f
}

fn splitmix64(mut x: u64) -> u64 {
    x ^= x >> 30; x = x.wrapping_mul(0xBF58_476D_1CE4_E5B9);
    x ^= x >> 27; x = x.wrapping_mul(0x94D0_49BB_1331_11EB);
    x ^ (x >> 31)
}
fn child_loc(depth: usize, ci: usize, parent: &[i64; 6]) -> [i64; 6] {
    if depth == 0 { return [0; 6]; }
    let h = splitmix64(((ci as u64 + 1) << 21) ^ ((depth as u64) * GOLDEN));
    let mut o = [0i64; 6];
    for d in 0..6 { o[d] = (parent[d] + (((h >> (8 * d)) & 0xFF) as i64) * depth as i64) & 0xFFFF; }
    o
}
fn walk(node: Node, depth: usize, ci: usize, parent: &[i64; 6], out: &mut Vec<[i64; 14]>) {
    let loc = child_loc(depth, ci, parent);
    let mut row = [0i64; 14];
    row[0] = node.kind_id() as i64;
    row[1] = depth as i64;
    row[2..8].copy_from_slice(&faces(node.kind()));
    row[8..14].copy_from_slice(&loc);
    out.push(row);
    for i in 0..node.named_child_count() {
        if let Some(c) = node.named_child(i) { walk(c, depth + 1, i, &loc, out); }
    }
}

fn parse(lang: &str, src: &str) -> Option<tree_sitter::Tree> {
    let language = language_for(lang)?;
    let mut p = Parser::new();
    p.set_language(&language).ok()?;
    p.parse(src.as_bytes(), None)
}

fn main() {
    let argv: Vec<String> = std::env::args().skip(1).collect();
    match argv.first().map(|s| s.as_str()) {
        Some("--langs") => {
            println!("{}", GRAMMARS.join(" "));
        }
        // --check <lang> <file>  -> report syntactic validity (compiles-shaped)
        Some("--check") => {
            let lang = argv.get(1).cloned().unwrap_or_default();
            let path = argv.get(2).cloned().unwrap_or_default();
            let src = std::fs::read_to_string(&path).unwrap_or_default();
            if language_for(&lang).is_none() {
                println!("{lang}\tNO_GRAMMAR\t{path}");
                std::process::exit(3);
            }
            match parse(&lang, &src) {
                Some(tree) => {
                    let root = tree.root_node();
                    let ok = !root.has_error();
                    println!("{lang}\t{}\t{path}\t({} named nodes)",
                             if ok { "OK" } else { "SYNTAX_ERROR" },
                             { let mut v = Vec::new(); walk(root, 0, 0, &[0; 6], &mut v); v.len() });
                    std::process::exit(if ok { 0 } else { 1 });
                }
                None => { println!("{lang}\tPARSE_FAIL\t{path}"); std::process::exit(2); }
            }
        }
        _ => {
            // encode mode: ast_cube_poly [lang] <file>
            let (lang, path) = if argv.len() >= 2 {
                (argv[0].clone(), argv[1].clone())
            } else if argv.len() == 1 {
                let p = argv[0].clone();
                let ext = std::path::Path::new(&p).extension().and_then(|s| s.to_str()).unwrap_or("");
                match lang_for_ext(ext) {
                    Some(l) => (l.to_string(), p),
                    None => { eprintln!("usage: ast_cube_poly [lang] <file> | --check <lang> <file> | --langs"); std::process::exit(2); }
                }
            } else {
                eprintln!("usage: ast_cube_poly [lang] <file> | --check <lang> <file> | --langs");
                std::process::exit(2);
            };
            let src = std::fs::read_to_string(&path).expect("read");
            match parse(&lang, &src) {
                Some(tree) => {
                    let mut out = Vec::new();
                    walk(tree.root_node(), 0, 0, &[0; 6], &mut out);
                    println!("ok[{lang}]: {} named nodes, error={}", out.len(), tree.root_node().has_error());
                }
                None => { eprintln!("parse/load failed for lang={lang}"); std::process::exit(1); }
            }
        }
    }
}
