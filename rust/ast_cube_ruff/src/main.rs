// ast_cube_ruff — AST cube encoder on ruff's fast parser (the 100x path).
//
// Same cube-vector semantics as ast_cube (type_id, depth, 6 Sacred-Tongue face
// trits, 6-D splitmix location), but parses with ruff's hand-written parser
// (~3.4x faster than rustpython's LALRPOP, and parse is 93% of encode time).
// Walks via ruff's SourceOrderVisitor: one enter_node per AST node.
//
// Node row: [type_id(kind discriminant), depth, KO, AV, RU, CA, UM, DR, loc x6]

#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

use ruff_python_ast::visitor::source_order::{walk_stmt, SourceOrderVisitor, TraversalSignal};
use ruff_python_ast::{AnyNodeRef, ExprContext, NodeKind};
use sha2::{Digest, Sha256};
use std::io::Write;
use std::time::Instant;

const VECTOR_DIM: usize = 14;
const GOLDEN: u64 = 0x9E37_79B1;

#[inline]
fn splitmix64(mut x: u64) -> u64 {
    x ^= x >> 30;
    x = x.wrapping_mul(0xBF58_476D_1CE4_E5B9);
    x ^= x >> 27;
    x = x.wrapping_mul(0x94D0_49BB_1331_11EB);
    x ^ (x >> 31)
}

#[inline]
fn child_loc(depth: usize, child_index: usize, parent: &[i64; 6]) -> [i64; 6] {
    if depth == 0 {
        return [0; 6];
    }
    let h = splitmix64(((child_index as u64 + 1) << 21) ^ ((depth as u64) * GOLDEN));
    let mut out = [0_i64; 6];
    for d in 0..6 {
        let byte = ((h >> (8 * d)) & 0xFF) as i64;
        out[d] = (parent[d] + byte * depth as i64) & 0xFFFF;
    }
    out
}

/// Base 6-face trits [KO, AV, RU, CA, UM, DR] from a ruff NodeKind.
/// Mirrors ast_cube's Sacred-Tongue FACE_RULES; ruff's split literals let us
/// classify constants without inspecting their value.
#[inline]
fn faces_of(kind: NodeKind) -> [i64; 6] {
    use NodeKind::*;
    match kind {
        // KO — Control Flow
        StmtIf | ExprIf | StmtFor | StmtWhile | StmtReturn | StmtBreak | StmtContinue
        | StmtMatch => [1, 0, 0, 0, 0, 0],
        StmtTry => [1, 0, 0, 0, 1, 0],      // KO + UM
        Comprehension => [1, 0, 1, 0, 0, 0], // KO + RU
        // AV — I/O
        ExprCall | ExprAttribute | StmtExpr | Parameters | Parameter | ParameterWithDefault
        | Keyword => [0, 1, 0, 0, 0, 0],
        StmtImport | StmtImportFrom => [0, 1, 0, 0, 1, 0], // AV + UM
        ExprFString | ExprTString => [0, 1, 0, 0, 0, 1],   // AV + DR (JoinedStr-like)
        // RU — Scope
        ModModule | StmtFunctionDef | StmtClassDef | ExprLambda | StmtWith => [0, 0, 1, 0, 0, 0],
        StmtGlobal | StmtNonlocal => [0, 0, 1, 0, 1, 0], // RU + UM
        // CA — Math/Logic (ruff splits Constant; numeric/bool/none -> CA)
        ExprBinOp | ExprUnaryOp | ExprBoolOp | ExprCompare | StmtAugAssign | ExprSubscript
        | ExprSlice | ExprNumberLiteral | ExprBooleanLiteral | ExprNoneLiteral
        | ExprEllipsisLiteral => [0, 0, 0, 1, 0, 0],
        // UM — Security
        StmtRaise | StmtAssert | StmtDelete => [0, 0, 0, 0, 1, 0],
        // DR — Transforms (string/bytes literal -> data)
        StmtAssign | StmtAnnAssign | ExprList | ExprTuple | ExprDict | ExprSet | ExprListComp
        | ExprDictComp | ExprSetComp | ExprGenerator | ExprStarred | ExprStringLiteral
        | ExprBytesLiteral => [0, 0, 0, 0, 0, 1],
        StmtPass => [-1, 0, 0, 0, 0, 0], // negative KO
        _ => [0, 0, 0, 0, 0, 0],
    }
}

struct Enc {
    depth: usize,
    counter: Vec<u32>,       // counter[d] = next child index for the depth-d parent
    loc_stack: Vec<[i64; 6]>, // loc_stack[d] = location of the depth-d ancestor
    matrix: Vec<[i64; VECTOR_DIM]>,
}

impl Enc {
    fn new(cap: usize) -> Self {
        Enc { depth: 0, counter: Vec::new(), loc_stack: Vec::new(), matrix: Vec::with_capacity(cap) }
    }

    /// Emit the Module root row (depth 0) and prime the stacks for its body.
    fn start_module(&mut self) {
        let loc = [0_i64; 6];
        let mut row = [0_i64; VECTOR_DIM];
        row[0] = NodeKind::ModModule as i64;
        row[2..8].copy_from_slice(&faces_of(NodeKind::ModModule));
        self.matrix.push(row);
        self.counter = vec![0];
        self.loc_stack = vec![loc];
        self.depth = 1;
    }
}

impl<'a> SourceOrderVisitor<'a> for Enc {
    fn enter_node(&mut self, node: AnyNodeRef<'a>) -> TraversalSignal {
        let d = self.depth;
        let (ci, parent_loc) = {
            let c = self.counter[d - 1];
            self.counter[d - 1] += 1;
            (c as usize, self.loc_stack[d - 1])
        };
        let loc = child_loc(d, ci, &parent_loc);
        let kind = node.kind();
        let mut tr = faces_of(kind);
        if let AnyNodeRef::ExprName(n) = node {
            match n.ctx {
                ExprContext::Store => { tr[1] = -1; tr[4] = 1; tr[5] = 1; }
                ExprContext::Load => { tr[1] = 1; tr[4] = -1; }
                ExprContext::Del => { tr[4] = 1; }
                _ => {}
            }
        }
        let mut row = [0_i64; VECTOR_DIM];
        row[0] = kind as i64;
        row[1] = d as i64;
        row[2..8].copy_from_slice(&tr);
        row[8..14].copy_from_slice(&loc);
        self.matrix.push(row);

        // prime child-tracking slots for this node's children
        if self.counter.len() <= d { self.counter.push(0); } else { self.counter[d] = 0; }
        if self.loc_stack.len() <= d { self.loc_stack.push(loc); } else { self.loc_stack[d] = loc; }
        self.depth += 1;
        TraversalSignal::Traverse
    }

    fn leave_node(&mut self, _node: AnyNodeRef<'a>) {
        self.depth -= 1;
    }
}

fn encode(src: &str) -> Option<Vec<[i64; VECTOR_DIM]>> {
    let parsed = ruff_python_parser::parse_module(src).ok()?;
    let module = parsed.syntax();
    let mut enc = Enc::new(src.len() / 8 + 8);
    enc.start_module();
    for stmt in &module.body {
        walk_stmt(&mut enc, stmt);
    }
    Some(enc.matrix)
}

// ---- corpus driver (parallel, binary output) ----

fn collect_py(root: &str, out: &mut Vec<std::path::PathBuf>) {
    let junk = ["node_modules", "pytest_temp_root", "liboqs", "__pycache__",
                "artifacts", "external", ".git", "target"];
    let mut stack = vec![std::path::PathBuf::from(root)];
    while let Some(dir) = stack.pop() {
        let rd = match std::fs::read_dir(&dir) { Ok(r) => r, Err(_) => continue };
        for ent in rd.flatten() {
            let p = ent.path();
            if p.is_dir() {
                let name = p.file_name().and_then(|s| s.to_str()).unwrap_or("");
                if !junk.contains(&name) { stack.push(p); }
            } else if p.extension().and_then(|s| s.to_str()) == Some("py") {
                out.push(p);
            }
        }
    }
}

fn newline_code(src: &str) -> u8 {
    if src.contains("\r\n") { 3 } else if src.contains('\r') { 2 } else if src.contains('\n') { 1 } else { 0 }
}

fn encode_record(path: &str, src: &str, matrix: &[[i64; VECTOR_DIM]], buf: &mut Vec<u8>) {
    let bytes = src.as_bytes();
    let hash = Sha256::digest(bytes);
    let pb = path.as_bytes();
    buf.extend_from_slice(&(pb.len() as u32).to_le_bytes());
    buf.extend_from_slice(pb);
    buf.extend_from_slice(&(bytes.len() as u64).to_le_bytes());
    buf.extend_from_slice(&(src.chars().count() as u64).to_le_bytes());
    buf.push(newline_code(src));
    buf.push(u8::from(src.ends_with('\n') || src.ends_with('\r')));
    buf.extend_from_slice(&hash);
    buf.extend_from_slice(&(bytes.len() as u64).to_le_bytes());
    buf.extend_from_slice(bytes);
    buf.extend_from_slice(&(matrix.len() as u64).to_le_bytes());
    for row in matrix {
        for v in row { buf.extend_from_slice(&v.to_le_bytes()); }
    }
}

fn corpus(root: &str, limit: usize, out: Option<&str>) {
    use std::sync::atomic::{AtomicU64, Ordering::Relaxed};
    let mut files = Vec::new();
    collect_py(root, &mut files);
    if files.len() > limit { files.truncate(limit); }
    let cores = std::thread::available_parallelism().map(|n| n.get()).unwrap_or(4);
    let want_out = out.is_some();

    // serial baseline
    let t0 = Instant::now();
    let (mut snodes, mut sok) = (0u64, 0u64);
    for f in &files {
        if let Ok(src) = std::fs::read_to_string(f) {
            if let Some(m) = encode(&src) { snodes += m.len() as u64; sok += 1; }
        }
    }
    let s_el = t0.elapsed().as_secs_f64();

    // parallel
    let chunk = (files.len() + cores - 1) / cores.max(1);
    let pnodes = AtomicU64::new(0);
    let pok = AtomicU64::new(0);
    let t1 = Instant::now();
    let parts: Vec<Vec<u8>> = std::thread::scope(|sc| {
        let handles: Vec<_> = files.chunks(chunk.max(1)).map(|ch| {
            let pnodes = &pnodes; let pok = &pok;
            sc.spawn(move || {
                let mut buf = Vec::new();
                let (mut ln, mut lok) = (0u64, 0u64);
                for f in ch {
                    if let Ok(src) = std::fs::read_to_string(f) {
                        if let Some(m) = encode(&src) {
                            ln += m.len() as u64; lok += 1;
                            if want_out { encode_record(&f.to_string_lossy(), &src, &m, &mut buf); }
                        }
                    }
                }
                pnodes.fetch_add(ln, Relaxed); pok.fetch_add(lok, Relaxed);
                buf
            })
        }).collect();
        handles.into_iter().map(|h| h.join().expect("thread")).collect()
    });
    let p_el = t1.elapsed().as_secs_f64();
    let pn = pnodes.load(Relaxed);
    let pk = pok.load(Relaxed);

    eprintln!("corpus(ruff): {} files ({} ok), {} cores, {} nodes", files.len(), pk, cores, pn);
    eprintln!("  serial   : {:>7.0} files/s   {:>11.0} nodes/s", sok as f64 / s_el, snodes as f64 / s_el);
    eprintln!("  parallel : {:>7.0} files/s   {:>11.0} nodes/s   ({:.1}x over serial)",
              pk as f64 / p_el, pn as f64 / p_el, s_el / p_el);

    if let Some(path) = out {
        let mut f = std::fs::File::create(path).expect("create out");
        f.write_all(b"SCBEAST2").expect("hdr");
        f.write_all(&(pk as u32).to_le_bytes()).expect("hdr");
        f.write_all(&(VECTOR_DIM as u32).to_le_bytes()).expect("hdr");
        for part in &parts { f.write_all(part).expect("body"); }
        eprintln!("  wrote {} -> {} bytes", path, 16 + parts.iter().map(|p| p.len()).sum::<usize>());
    }
}

fn main() {
    let mut corpus_mode = false;
    let mut limit = usize::MAX;
    let mut out: Option<String> = None;
    let mut paths: Vec<String> = Vec::new();
    let mut argv = std::env::args().skip(1);
    while let Some(arg) = argv.next() {
        match arg.as_str() {
            "--corpus" => corpus_mode = true,
            "--limit" => limit = argv.next().and_then(|s| s.parse().ok()).unwrap_or(usize::MAX),
            "--out" => out = argv.next(),
            _ => paths.push(arg),
        }
    }
    if corpus_mode {
        let root = paths.first().cloned().unwrap_or_else(|| ".".to_string());
        corpus(&root, limit, out.as_deref());
        return;
    }
    let path = match paths.first() {
        Some(p) => p.clone(),
        None => { eprintln!("usage: ast_cube_ruff <file.py> | --corpus <root> [--limit N] [--out f.bin]"); std::process::exit(2); }
    };
    let src = std::fs::read_to_string(&path).expect("read");
    let t = Instant::now();
    match encode(&src) {
        Some(m) => println!("ok: {} nodes in {:?}", m.len(), t.elapsed()),
        None => { eprintln!("parse error"); std::process::exit(1); }
    }
}
