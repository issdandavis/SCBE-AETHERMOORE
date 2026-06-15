#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

use base64::Engine;
use rustpython_parser::{ast, Parse};
use serde_json::json;
use sha2::{Digest, Sha256};
use std::io::{self, Write};
use std::time::Instant;

const VECTOR_DIM: usize = 14;
const GOLDEN: u64 = 0x9E37_79B1;

fn type_id(ntype: &str) -> i64 {
    match ntype {
        "Module" => 1,
        "FunctionDef" => 2,
        "AsyncFunctionDef" => 3,
        "ClassDef" => 4,
        "Return" => 5,
        "Assign" => 6,
        "AugAssign" => 7,
        "AnnAssign" => 8,
        "For" => 9,
        "While" => 10,
        "If" => 11,
        "With" => 12,
        "Raise" => 13,
        "Try" => 14,
        "Import" => 15,
        "ImportFrom" => 16,
        "Expr" => 17,
        "Call" => 18,
        "Name" => 19,
        "Attribute" => 20,
        "Constant" => 21,
        "BinOp" => 22,
        "UnaryOp" => 23,
        "BoolOp" => 24,
        "Compare" => 25,
        "arguments" => 26,
        "arg" => 27,
        "keyword" => 28,
        "List" => 29,
        "Tuple" => 30,
        "Dict" => 31,
        "Set" => 32,
        "Subscript" => 33,
        "Lambda" => 34,
        "comprehension" => 35,
        "ListComp" => 36,
        "DictComp" => 37,
        "GeneratorExp" => 38,
        "Starred" => 39,
        "Slice" => 40,
        "JoinedStr" => 41,
        _ => 0,
    }
}

fn splitmix64(mut x: u64) -> u64 {
    x ^= x >> 30;
    x = x.wrapping_mul(0xBF58_476D_1CE4_E5B9);
    x ^= x >> 27;
    x = x.wrapping_mul(0x94D0_49BB_1331_11EB);
    x ^ (x >> 31)
}

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

/// Base 6-face trits [KO, AV, RU, CA, UM, DR] from the node's structural role.
/// One match replaces six per-tongue string scans — same output as FACE_RULES
/// membership (a node in N tongue-sets lights all N axes).
#[inline]
fn base_faces(ntype: &str) -> [i64; 6] {
    match ntype {
        "If" | "IfExp" | "For" | "AsyncFor" | "While" | "Return" | "Break"
        | "Continue" | "Match" => [1, 0, 0, 0, 0, 0],
        "Try" => [1, 0, 0, 0, 1, 0], // KO + UM
        "comprehension" => [1, 0, 1, 0, 0, 0], // KO + RU
        "Call" | "Attribute" | "Expr" | "arguments" | "arg" | "keyword" => [0, 1, 0, 0, 0, 0],
        "Import" | "ImportFrom" => [0, 1, 0, 0, 1, 0], // AV + UM
        "JoinedStr" => [0, 1, 0, 0, 0, 1], // AV + DR
        "Module" | "FunctionDef" | "AsyncFunctionDef" | "ClassDef" | "Lambda"
        | "With" | "AsyncWith" => [0, 0, 1, 0, 0, 0],
        "Global" | "Nonlocal" => [0, 0, 1, 0, 1, 0], // RU + UM
        "BinOp" | "UnaryOp" | "BoolOp" | "Compare" | "AugAssign" | "Subscript"
        | "Slice" | "Constant" => [0, 0, 0, 1, 0, 0],
        "Raise" | "Assert" | "Delete" => [0, 0, 0, 0, 1, 0],
        "Assign" | "AnnAssign" | "List" | "Tuple" | "Dict" | "Set" | "ListComp"
        | "DictComp" | "SetComp" | "GeneratorExp" | "Starred" => [0, 0, 0, 0, 0, 1],
        "Pass" => [-1, 0, 0, 0, 0, 0], // negative KO
        _ => [0, 0, 0, 0, 0, 0],
    }
}

fn face_trits(
    ntype: &str,
    name_ctx: Option<ast::ExprContext>,
    constant: Option<&ast::Constant>,
) -> [i64; 6] {
    let mut tr = base_faces(ntype);
    if let Some(ctx) = name_ctx {
        match ctx {
            ast::ExprContext::Store => {
                tr[1] = -1;
                tr[4] = 1;
                tr[5] = 1;
            }
            ast::ExprContext::Load => {
                tr[1] = 1;
                tr[4] = -1;
            }
            ast::ExprContext::Del => {
                tr[4] = 1;
            }
        }
    }
    if let Some(value) = constant {
        match value {
            ast::Constant::Str(_) | ast::Constant::Bytes(_) => tr[5] = 1,
            ast::Constant::None
            | ast::Constant::Bool(_)
            | ast::Constant::Int(_)
            | ast::Constant::Float(_)
            | ast::Constant::Complex { .. } => tr[3] = 1,
            _ => {}
        }
    }
    tr
}

fn push_row(
    matrix: &mut Vec<[i64; VECTOR_DIM]>,
    ntype: &str,
    depth: usize,
    loc: &[i64; 6],
    tr: [i64; 6],
) {
    let mut row = [0_i64; VECTOR_DIM];
    row[0] = type_id(ntype);
    row[1] = depth as i64;
    row[2..8].copy_from_slice(&tr);
    row[8..14].copy_from_slice(loc);
    matrix.push(row);
}

fn walk_args(
    args: &ast::Arguments,
    depth: usize,
    child_index: usize,
    parent: &[i64; 6],
    matrix: &mut Vec<[i64; VECTOR_DIM]>,
) {
    let loc = child_loc(depth, child_index, parent);
    push_row(
        matrix,
        "arguments",
        depth,
        &loc,
        face_trits("arguments", None, None),
    );
    let mut ci = 0;
    for a in args
        .posonlyargs
        .iter()
        .chain(args.args.iter())
        .chain(args.kwonlyargs.iter())
    {
        walk_arg(&a.def, depth + 1, ci, &loc, matrix);
        ci += 1;
        if let Some(default) = &a.default {
            walk_expr(default, depth + 1, ci, &loc, matrix);
            ci += 1;
        }
    }
    if let Some(a) = &args.vararg {
        walk_arg(a, depth + 1, ci, &loc, matrix);
        ci += 1;
    }
    if let Some(a) = &args.kwarg {
        walk_arg(a, depth + 1, ci, &loc, matrix);
    }
}

fn walk_arg(
    arg: &ast::Arg,
    depth: usize,
    child_index: usize,
    parent: &[i64; 6],
    matrix: &mut Vec<[i64; VECTOR_DIM]>,
) {
    let loc = child_loc(depth, child_index, parent);
    push_row(matrix, "arg", depth, &loc, face_trits("arg", None, None));
    if let Some(annotation) = &arg.annotation {
        walk_expr(annotation, depth + 1, 0, &loc, matrix);
    }
}

fn walk_stmt(
    stmt: &ast::Stmt,
    depth: usize,
    child_index: usize,
    parent: &[i64; 6],
    matrix: &mut Vec<[i64; VECTOR_DIM]>,
) {
    use ast::Stmt::*;
    let loc = child_loc(depth, child_index, parent);
    let ntype = match stmt {
        FunctionDef(_) => "FunctionDef",
        AsyncFunctionDef(_) => "AsyncFunctionDef",
        ClassDef(_) => "ClassDef",
        Return(_) => "Return",
        Delete(_) => "Delete",
        Assign(_) => "Assign",
        TypeAlias(_) => "TypeAlias",
        AugAssign(_) => "AugAssign",
        AnnAssign(_) => "AnnAssign",
        For(_) => "For",
        AsyncFor(_) => "AsyncFor",
        While(_) => "While",
        If(_) => "If",
        With(_) => "With",
        AsyncWith(_) => "AsyncWith",
        Match(_) => "Match",
        Raise(_) => "Raise",
        Try(_) => "Try",
        TryStar(_) => "Try",
        Assert(_) => "Assert",
        Import(_) => "Import",
        ImportFrom(_) => "ImportFrom",
        Global(_) => "Global",
        Nonlocal(_) => "Nonlocal",
        Expr(_) => "Expr",
        Pass(_) => "Pass",
        Break(_) => "Break",
        Continue(_) => "Continue",
    };
    push_row(matrix, ntype, depth, &loc, face_trits(ntype, None, None));
    let mut ci = 0;
    match stmt {
        FunctionDef(s) => {
            walk_args(&s.args, depth + 1, ci, &loc, matrix);
            ci += 1;
            for e in &s.decorator_list {
                walk_expr(e, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
            if let Some(e) = &s.returns {
                walk_expr(e, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
            for st in &s.body {
                walk_stmt(st, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
        }
        AsyncFunctionDef(s) => {
            walk_args(&s.args, depth + 1, ci, &loc, matrix);
            ci += 1;
            for e in &s.decorator_list {
                walk_expr(e, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
            if let Some(e) = &s.returns {
                walk_expr(e, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
            for st in &s.body {
                walk_stmt(st, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
        }
        ClassDef(s) => {
            for e in &s.bases {
                walk_expr(e, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
            for k in &s.keywords {
                walk_keyword(k, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
            for e in &s.decorator_list {
                walk_expr(e, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
            for st in &s.body {
                walk_stmt(st, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
        }
        Return(s) => {
            if let Some(e) = &s.value {
                walk_expr(e, depth + 1, ci, &loc, matrix);
            }
        }
        Delete(s) => {
            for e in &s.targets {
                walk_expr(e, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
        }
        Assign(s) => {
            for e in &s.targets {
                walk_expr(e, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
            walk_expr(&s.value, depth + 1, ci, &loc, matrix);
        }
        AugAssign(s) => {
            walk_expr(&s.target, depth + 1, 0, &loc, matrix);
            walk_expr(&s.value, depth + 1, 1, &loc, matrix);
        }
        AnnAssign(s) => {
            walk_expr(&s.target, depth + 1, 0, &loc, matrix);
            walk_expr(&s.annotation, depth + 1, 1, &loc, matrix);
            if let Some(e) = &s.value {
                walk_expr(e, depth + 1, 2, &loc, matrix);
            }
        }
        For(s) => {
            walk_expr(&s.target, depth + 1, ci, &loc, matrix);
            ci += 1;
            walk_expr(&s.iter, depth + 1, ci, &loc, matrix);
            ci += 1;
            for st in &s.body {
                walk_stmt(st, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
            for st in &s.orelse {
                walk_stmt(st, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
        }
        AsyncFor(s) => {
            walk_expr(&s.target, depth + 1, ci, &loc, matrix);
            ci += 1;
            walk_expr(&s.iter, depth + 1, ci, &loc, matrix);
            ci += 1;
            for st in &s.body {
                walk_stmt(st, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
            for st in &s.orelse {
                walk_stmt(st, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
        }
        While(s) => {
            walk_expr(&s.test, depth + 1, ci, &loc, matrix);
            ci += 1;
            for st in &s.body {
                walk_stmt(st, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
            for st in &s.orelse {
                walk_stmt(st, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
        }
        If(s) => {
            walk_expr(&s.test, depth + 1, ci, &loc, matrix);
            ci += 1;
            for st in &s.body {
                walk_stmt(st, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
            for st in &s.orelse {
                walk_stmt(st, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
        }
        With(s) => {
            for item in &s.items {
                walk_expr(&item.context_expr, depth + 1, ci, &loc, matrix);
                ci += 1;
                if let Some(e) = &item.optional_vars {
                    walk_expr(e, depth + 1, ci, &loc, matrix);
                    ci += 1;
                }
            }
            for st in &s.body {
                walk_stmt(st, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
        }
        AsyncWith(s) => {
            for item in &s.items {
                walk_expr(&item.context_expr, depth + 1, ci, &loc, matrix);
                ci += 1;
                if let Some(e) = &item.optional_vars {
                    walk_expr(e, depth + 1, ci, &loc, matrix);
                    ci += 1;
                }
            }
            for st in &s.body {
                walk_stmt(st, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
        }
        Raise(s) => {
            if let Some(e) = &s.exc {
                walk_expr(e, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
            if let Some(e) = &s.cause {
                walk_expr(e, depth + 1, ci, &loc, matrix);
            }
        }
        Try(s) => {
            for st in &s.body {
                walk_stmt(st, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
            for h in &s.handlers {
                walk_handler(h, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
            for st in &s.orelse {
                walk_stmt(st, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
            for st in &s.finalbody {
                walk_stmt(st, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
        }
        TryStar(s) => {
            for st in &s.body {
                walk_stmt(st, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
            for h in &s.handlers {
                walk_handler(h, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
            for st in &s.orelse {
                walk_stmt(st, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
            for st in &s.finalbody {
                walk_stmt(st, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
        }
        Assert(s) => {
            walk_expr(&s.test, depth + 1, 0, &loc, matrix);
            if let Some(e) = &s.msg {
                walk_expr(e, depth + 1, 1, &loc, matrix);
            }
        }
        Expr(s) => walk_expr(&s.value, depth + 1, 0, &loc, matrix),
        Import(_) | ImportFrom(_) | Global(_) | Nonlocal(_) | Pass(_) | Break(_) | Continue(_)
        | TypeAlias(_) | Match(_) => {}
    }
}

fn walk_handler(
    handler: &ast::ExceptHandler,
    depth: usize,
    child_index: usize,
    parent: &[i64; 6],
    matrix: &mut Vec<[i64; VECTOR_DIM]>,
) {
    let loc = child_loc(depth, child_index, parent);
    push_row(
        matrix,
        "ExceptHandler",
        depth,
        &loc,
        face_trits("Try", None, None),
    );
    let ast::ExceptHandler::ExceptHandler(h) = handler;
    let mut ci = 0;
    if let Some(e) = &h.type_ {
        walk_expr(e, depth + 1, ci, &loc, matrix);
        ci += 1;
    }
    for st in &h.body {
        walk_stmt(st, depth + 1, ci, &loc, matrix);
        ci += 1;
    }
}

fn walk_keyword(
    keyword: &ast::Keyword,
    depth: usize,
    child_index: usize,
    parent: &[i64; 6],
    matrix: &mut Vec<[i64; VECTOR_DIM]>,
) {
    let loc = child_loc(depth, child_index, parent);
    push_row(
        matrix,
        "keyword",
        depth,
        &loc,
        face_trits("keyword", None, None),
    );
    walk_expr(&keyword.value, depth + 1, 0, &loc, matrix);
}

fn walk_comprehension(
    comp: &ast::Comprehension,
    depth: usize,
    child_index: usize,
    parent: &[i64; 6],
    matrix: &mut Vec<[i64; VECTOR_DIM]>,
) {
    let loc = child_loc(depth, child_index, parent);
    push_row(
        matrix,
        "comprehension",
        depth,
        &loc,
        face_trits("comprehension", None, None),
    );
    let mut ci = 0;
    walk_expr(&comp.target, depth + 1, ci, &loc, matrix);
    ci += 1;
    walk_expr(&comp.iter, depth + 1, ci, &loc, matrix);
    ci += 1;
    for e in &comp.ifs {
        walk_expr(e, depth + 1, ci, &loc, matrix);
        ci += 1;
    }
}

fn walk_expr(
    expr: &ast::Expr,
    depth: usize,
    child_index: usize,
    parent: &[i64; 6],
    matrix: &mut Vec<[i64; VECTOR_DIM]>,
) {
    use ast::Expr::*;
    let loc = child_loc(depth, child_index, parent);
    let (ntype, ctx, constant) = match expr {
        BoolOp(_) => ("BoolOp", None, None),
        NamedExpr(_) => ("NamedExpr", None, None),
        BinOp(_) => ("BinOp", None, None),
        UnaryOp(_) => ("UnaryOp", None, None),
        Lambda(_) => ("Lambda", None, None),
        IfExp(_) => ("IfExp", None, None),
        Dict(_) => ("Dict", None, None),
        Set(_) => ("Set", None, None),
        ListComp(_) => ("ListComp", None, None),
        SetComp(_) => ("SetComp", None, None),
        DictComp(_) => ("DictComp", None, None),
        GeneratorExp(_) => ("GeneratorExp", None, None),
        Await(_) => ("Await", None, None),
        Yield(_) => ("Yield", None, None),
        YieldFrom(_) => ("YieldFrom", None, None),
        Compare(_) => ("Compare", None, None),
        Call(_) => ("Call", None, None),
        FormattedValue(_) => ("FormattedValue", None, None),
        JoinedStr(_) => ("JoinedStr", None, None),
        Constant(e) => ("Constant", None, Some(&e.value)),
        Attribute(e) => ("Attribute", Some(e.ctx), None),
        Subscript(e) => ("Subscript", Some(e.ctx), None),
        Starred(e) => ("Starred", Some(e.ctx), None),
        Name(e) => ("Name", Some(e.ctx), None),
        List(e) => ("List", Some(e.ctx), None),
        Tuple(e) => ("Tuple", Some(e.ctx), None),
        Slice(_) => ("Slice", None, None),
    };
    push_row(matrix, ntype, depth, &loc, face_trits(ntype, ctx, constant));
    let mut ci = 0;
    match expr {
        BoolOp(e) => {
            for v in &e.values {
                walk_expr(v, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
        }
        NamedExpr(e) => {
            walk_expr(&e.target, depth + 1, 0, &loc, matrix);
            walk_expr(&e.value, depth + 1, 1, &loc, matrix);
        }
        BinOp(e) => {
            walk_expr(&e.left, depth + 1, 0, &loc, matrix);
            walk_expr(&e.right, depth + 1, 1, &loc, matrix);
        }
        UnaryOp(e) => walk_expr(&e.operand, depth + 1, 0, &loc, matrix),
        Lambda(e) => {
            walk_args(&e.args, depth + 1, 0, &loc, matrix);
            walk_expr(&e.body, depth + 1, 1, &loc, matrix);
        }
        IfExp(e) => {
            walk_expr(&e.test, depth + 1, 0, &loc, matrix);
            walk_expr(&e.body, depth + 1, 1, &loc, matrix);
            walk_expr(&e.orelse, depth + 1, 2, &loc, matrix);
        }
        Dict(e) => {
            for k in e.keys.iter().flatten() {
                walk_expr(k, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
            for v in &e.values {
                walk_expr(v, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
        }
        Set(e) => {
            for v in &e.elts {
                walk_expr(v, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
        }
        ListComp(e) => {
            walk_expr(&e.elt, depth + 1, ci, &loc, matrix);
            ci += 1;
            for c in &e.generators {
                walk_comprehension(c, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
        }
        SetComp(e) => {
            walk_expr(&e.elt, depth + 1, ci, &loc, matrix);
            ci += 1;
            for c in &e.generators {
                walk_comprehension(c, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
        }
        DictComp(e) => {
            walk_expr(&e.key, depth + 1, ci, &loc, matrix);
            ci += 1;
            walk_expr(&e.value, depth + 1, ci, &loc, matrix);
            ci += 1;
            for c in &e.generators {
                walk_comprehension(c, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
        }
        GeneratorExp(e) => {
            walk_expr(&e.elt, depth + 1, ci, &loc, matrix);
            ci += 1;
            for c in &e.generators {
                walk_comprehension(c, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
        }
        Await(e) => walk_expr(&e.value, depth + 1, 0, &loc, matrix),
        Yield(e) => {
            if let Some(v) = &e.value {
                walk_expr(v, depth + 1, 0, &loc, matrix);
            }
        }
        YieldFrom(e) => walk_expr(&e.value, depth + 1, 0, &loc, matrix),
        Compare(e) => {
            walk_expr(&e.left, depth + 1, ci, &loc, matrix);
            ci += 1;
            for c in &e.comparators {
                walk_expr(c, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
        }
        Call(e) => {
            walk_expr(&e.func, depth + 1, ci, &loc, matrix);
            ci += 1;
            for a in &e.args {
                walk_expr(a, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
            for k in &e.keywords {
                walk_keyword(k, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
        }
        FormattedValue(e) => {
            walk_expr(&e.value, depth + 1, ci, &loc, matrix);
            ci += 1;
            if let Some(f) = &e.format_spec {
                walk_expr(f, depth + 1, ci, &loc, matrix);
            }
        }
        JoinedStr(e) => {
            for v in &e.values {
                walk_expr(v, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
        }
        Attribute(e) => walk_expr(&e.value, depth + 1, 0, &loc, matrix),
        Subscript(e) => {
            walk_expr(&e.value, depth + 1, 0, &loc, matrix);
            walk_expr(&e.slice, depth + 1, 1, &loc, matrix);
        }
        Starred(e) => walk_expr(&e.value, depth + 1, 0, &loc, matrix),
        List(e) => {
            for v in &e.elts {
                walk_expr(v, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
        }
        Tuple(e) => {
            for v in &e.elts {
                walk_expr(v, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
        }
        Slice(e) => {
            if let Some(v) = &e.lower {
                walk_expr(v, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
            if let Some(v) = &e.upper {
                walk_expr(v, depth + 1, ci, &loc, matrix);
                ci += 1;
            }
            if let Some(v) = &e.step {
                walk_expr(v, depth + 1, ci, &loc, matrix);
            }
        }
        Constant(_) | Name(_) => {}
    }
}

fn source_layer(src: &str) -> serde_json::Value {
    let bytes = src.as_bytes();
    let hash = Sha256::digest(bytes);
    let newline_style = if src.contains("\r\n") {
        "crlf"
    } else if src.contains('\r') {
        "cr"
    } else if src.contains('\n') {
        "lf"
    } else {
        "none"
    };
    json!({
        "schema": "scbe_ast_source_bijection_v1",
        "encoding": "utf-8",
        "source_utf8_b64": base64::engine::general_purpose::STANDARD.encode(bytes),
        "source_sha256": format!("{:x}", hash),
        "char_count": src.chars().count(),
        "byte_count": bytes.len(),
        "newline_style": newline_style,
        "has_trailing_newline": src.ends_with('\n') || src.ends_with('\r')
    })
}

fn matrix_for_source(path: &str, src: &str) -> (Vec<[i64; VECTOR_DIM]>, f64, f64) {
    let t0 = Instant::now();
    let suite = ast::Suite::parse(&src, &path).unwrap_or_else(|e| {
        eprintln!("parse error: {e}");
        std::process::exit(1);
    });
    let parse_ms = t0.elapsed().as_secs_f64() * 1000.0;
    let t1 = Instant::now();
    let mut matrix: Vec<[i64; VECTOR_DIM]> = Vec::with_capacity(src.len() / 8);
    let root = [0_i64; 6];
    push_row(
        &mut matrix,
        "Module",
        0,
        &root,
        face_trits("Module", None, None),
    );
    for (i, stmt) in suite.iter().enumerate() {
        walk_stmt(stmt, 1, i, &root, &mut matrix);
    }
    let walk_ms = t1.elapsed().as_secs_f64() * 1000.0;
    (matrix, parse_ms, walk_ms)
}

fn encode_path(path: &str, include_matrix: bool) -> serde_json::Value {
    let src = std::fs::read_to_string(&path).expect("read file as UTF-8");
    let (matrix, parse_ms, walk_ms) = matrix_for_source(path, &src);
    let mut out = json!({
        "schema": "scbe_ast_cube_rust_v1",
        "source_path": path,
        "shape": [matrix.len(), VECTOR_DIM],
        "bijective": source_layer(&src),
        "face_legend": {
            "KO": "Control Flow",
            "AV": "I/O",
            "RU": "Scope",
            "CA": "Math/Logic",
            "UM": "Security",
            "DR": "Transforms"
        },
        "timing_ms": {
            "parse": parse_ms,
            "walk": walk_ms,
            "total": parse_ms + walk_ms
        }
    });
    if include_matrix {
        out["matrix"] = json!(matrix);
    }
    out
}

fn newline_style_code(src: &str) -> u8 {
    if src.contains("\r\n") {
        3
    } else if src.contains('\r') {
        2
    } else if src.contains('\n') {
        1
    } else {
        0
    }
}

fn write_u8(out: &mut dyn Write, value: u8) -> io::Result<()> {
    out.write_all(&[value])
}

fn write_u32(out: &mut dyn Write, value: u32) -> io::Result<()> {
    out.write_all(&value.to_le_bytes())
}

fn write_u64(out: &mut dyn Write, value: u64) -> io::Result<()> {
    out.write_all(&value.to_le_bytes())
}

fn write_i64(out: &mut dyn Write, value: i64) -> io::Result<()> {
    out.write_all(&value.to_le_bytes())
}

fn write_binary(paths: &[String]) -> io::Result<()> {
    let mut stdout = io::stdout().lock();
    stdout.write_all(b"SCBEAST2")?;
    write_u32(&mut stdout, paths.len() as u32)?;
    write_u32(&mut stdout, VECTOR_DIM as u32)?;
    for path in paths {
        let src = std::fs::read_to_string(path).expect("read file as UTF-8");
        let bytes = src.as_bytes();
        let hash = Sha256::digest(bytes);
        let (matrix, _parse_ms, _walk_ms) = matrix_for_source(path, &src);
        let path_bytes = path.as_bytes();

        write_u32(&mut stdout, path_bytes.len() as u32)?;
        stdout.write_all(path_bytes)?;
        write_u64(&mut stdout, bytes.len() as u64)?;
        write_u64(&mut stdout, src.chars().count() as u64)?;
        write_u8(&mut stdout, newline_style_code(&src))?;
        write_u8(
            &mut stdout,
            u8::from(src.ends_with('\n') || src.ends_with('\r')),
        )?;
        stdout.write_all(&hash)?;
        write_u64(&mut stdout, bytes.len() as u64)?;
        stdout.write_all(bytes)?;
        write_u64(&mut stdout, matrix.len() as u64)?;
        for row in &matrix {
            for value in row {
                write_i64(&mut stdout, *value)?;
            }
        }
    }
    Ok(())
}

// ---- parallel corpus encoder: the 100x path (in-process threads, no GIL) ----

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

/// Parse-safe encode: returns None on parse error instead of exiting (corpus-safe).
fn try_matrix(path: &str, src: &str) -> Option<Vec<[i64; VECTOR_DIM]>> {
    let suite = ast::Suite::parse(src, path).ok()?;
    let mut matrix: Vec<[i64; VECTOR_DIM]> = Vec::with_capacity(src.len() / 8);
    let root = [0_i64; 6];
    push_row(&mut matrix, "Module", 0, &root, face_trits("Module", None, None));
    for (i, stmt) in suite.iter().enumerate() {
        walk_stmt(stmt, 1, i, &root, &mut matrix);
    }
    Some(matrix)
}

/// Append one file's binary record (same layout as write_binary's per-file block).
fn encode_record(path: &str, src: &str, matrix: &[[i64; VECTOR_DIM]], buf: &mut Vec<u8>) {
    let bytes = src.as_bytes();
    let hash = Sha256::digest(bytes);
    let pb = path.as_bytes();
    buf.extend_from_slice(&(pb.len() as u32).to_le_bytes());
    buf.extend_from_slice(pb);
    buf.extend_from_slice(&(bytes.len() as u64).to_le_bytes());
    buf.extend_from_slice(&(src.chars().count() as u64).to_le_bytes());
    buf.push(newline_style_code(src));
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

    // serial baseline (single thread)
    let t0 = Instant::now();
    let (mut snodes, mut sok) = (0u64, 0u64);
    for f in &files {
        if let Ok(src) = std::fs::read_to_string(f) {
            if let Some(m) = try_matrix(&f.to_string_lossy(), &src) { snodes += m.len() as u64; sok += 1; }
        }
    }
    let s_el = t0.elapsed().as_secs_f64();

    // parallel across cores
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
                        let p = f.to_string_lossy();
                        if let Some(m) = try_matrix(&p, &src) {
                            ln += m.len() as u64; lok += 1;
                            if want_out { encode_record(&p, &src, &m, &mut buf); }
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

    eprintln!("corpus: {} files ({} ok), {} cores, {} nodes", files.len(), pk, cores, pn);
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
    let mut include_matrix = true;
    let mut binary = false;
    let mut corpus_mode = false;
    let mut limit = usize::MAX;
    let mut out: Option<String> = None;
    let mut paths: Vec<String> = Vec::new();
    let mut argv = std::env::args().skip(1).peekable();
    while let Some(arg) = argv.next() {
        match arg.as_str() {
            "--summary" | "--no-matrix" => include_matrix = false,
            "--binary" | "--bin" => binary = true,
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
    if paths.is_empty() {
        eprintln!("usage: ast_cube [--summary|--binary] <file.py> [more.py ...]");
        eprintln!("       ast_cube --corpus <root> [--limit N] [--out file.bin]");
        std::process::exit(2);
    }
    if binary {
        if let Err(err) = write_binary(&paths) {
            eprintln!("binary write error: {err}");
            std::process::exit(1);
        }
        return;
    }
    if paths.len() == 1 {
        let out = encode_path(&paths[0], include_matrix);
        println!("{}", serde_json::to_string(&out).expect("serialize"));
        return;
    }
    let t0 = Instant::now();
    let files: Vec<serde_json::Value> = paths
        .iter()
        .map(|p| encode_path(p, include_matrix))
        .collect();
    let elapsed_ms = t0.elapsed().as_secs_f64() * 1000.0;
    let node_count: usize = files
        .iter()
        .map(|f| f["shape"][0].as_u64().unwrap_or(0) as usize)
        .sum();
    let out = json!({
        "schema": "scbe_ast_cube_rust_batch_v1",
        "file_count": files.len(),
        "node_count": node_count,
        "timing_ms": {"total": elapsed_ms},
        "files": files
    });
    println!("{}", serde_json::to_string(&out).expect("serialize"));
}
