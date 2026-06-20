// Legacy syntax validator (tree-sitter 0.20) for the old-ABI grammar faces:
// csharp, lua, kotlin, swift, zig — which pin a runtime incompatible with 0.24.
use tree_sitter::{Language, Parser};

fn language_for(name: &str) -> Option<Language> {
    Some(match name {
        "csharp" => tree_sitter_c_sharp::language(),
        "lua" => tree_sitter_lua::language(),
        "kotlin" => tree_sitter_kotlin::language(),
        "swift" => tree_sitter_swift::language(),
        "zig" => tree_sitter_zig::language(),
        _ => return None,
    })
}

fn main() {
    let a: Vec<String> = std::env::args().skip(1).collect();
    if a.first().map(|s| s.as_str()) != Some("--check") || a.len() < 3 {
        eprintln!("usage: ast_cube_poly_legacy --check <lang> <file>");
        std::process::exit(2);
    }
    let (lang, path) = (&a[1], &a[2]);
    let src = std::fs::read_to_string(path).unwrap_or_default();
    let mut p = Parser::new();
    match language_for(lang) {
        Some(l) => if p.set_language(l).is_err() { println!("{lang}\tABI_FAIL\t{path}"); std::process::exit(2); },
        None => { println!("{lang}\tNO_GRAMMAR\t{path}"); std::process::exit(3); }
    }
    match p.parse(src.as_bytes(), None) {
        Some(t) => {
            let ok = !t.root_node().has_error();
            println!("{lang}\t{}\t{path}", if ok { "OK" } else { "SYNTAX_ERROR" });
            std::process::exit(if ok { 0 } else { 1 });
        }
        None => { println!("{lang}\tPARSE_FAIL\t{path}"); std::process::exit(2); }
    }
}
