// Polyglot cube encoder — de-risk: does tree-sitter compile + parse on MSVC?
use tree_sitter::{Node, Parser};

fn faces(kind: &str) -> [i64; 6] {
    // universal substring map: one face logic across all grammars (KO,AV,RU,CA,UM,DR)
    let has = |ns: &[&str]| ns.iter().any(|n| kind.contains(n));
    let mut f = [0i64; 6];
    if has(&["if", "for", "while", "switch", "case", "return", "break", "continue",
             "loop", "ternary", "conditional", "match", "yield", "goto"]) { f[0] = 1; }
    if has(&["call", "import", "include", "require", "argument", "parameter",
             "await", "export", "print"]) { f[1] = 1; }
    if has(&["function", "method", "class", "module", "namespace", "struct", "impl",
             "trait", "interface", "enum", "block", "lambda", "closure", "program",
             "package", "definition"]) { f[2] = 1; }
    if has(&["binary", "unary", "number", "integer", "float", "comparison",
             "arithmetic", "subscript", "index", "boolean", "operator", "bitwise"]) { f[3] = 1; }
    if has(&["try", "catch", "throw", "raise", "assert", "unsafe", "delete",
             "except", "finally", "panic"]) { f[4] = 1; }
    if has(&["assign", "declaration", "array", "list", "object", "dictionary",
             "map", "tuple", "string", "template", "literal", "spread"]) { f[5] = 1; }
    f
}

const GOLDEN: u64 = 0x9E37_79B1;
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
    let n = node.named_child_count();
    for i in 0..n {
        walk(node.named_child(i).unwrap(), depth + 1, i, &loc, out);
    }
}

fn main() {
    let path = std::env::args().nth(1).expect("usage: ast_cube_poly <file.js>");
    let src = std::fs::read_to_string(&path).expect("read");
    let mut p = Parser::new();
    p.set_language(&tree_sitter_javascript::LANGUAGE.into()).expect("load grammar");
    let t = std::time::Instant::now();
    let tree = p.parse(src.as_bytes(), None).expect("parse");
    let mut out = Vec::new();
    walk(tree.root_node(), 0, 0, &[0; 6], &mut out);
    println!("ok: {} named nodes in {:?}  root={}", out.len(), t.elapsed(), tree.root_node().kind());
    println!("first rows: {:?}", &out[..out.len().min(3)]);
}
