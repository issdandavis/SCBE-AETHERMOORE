use rustpython_parser::Parse;
use std::time::Instant;

fn collect(root: &str, out: &mut Vec<std::path::PathBuf>) {
    let junk = ["node_modules","__pycache__","liboqs","target",".git","external"];
    let mut st = vec![std::path::PathBuf::from(root)];
    while let Some(d) = st.pop() {
        let rd = match std::fs::read_dir(&d){Ok(r)=>r,Err(_)=>continue};
        for e in rd.flatten() {
            let p = e.path();
            if p.is_dir() {
                let n = p.file_name().and_then(|s|s.to_str()).unwrap_or("");
                if !junk.contains(&n) { st.push(p); }
            } else if p.extension().and_then(|s|s.to_str())==Some("py") { out.push(p); }
        }
    }
}

fn main() {
    let root = std::env::args().nth(1).unwrap_or("../../".into());
    let mut files = Vec::new(); collect(&root, &mut files); files.truncate(2000);
    let srcs: Vec<(String,String)> = files.iter()
        .filter_map(|f| std::fs::read_to_string(f).ok().map(|s|(f.to_string_lossy().into_owned(), s)))
        .collect();
    let total_bytes: usize = srcs.iter().map(|(_,s)|s.len()).sum();

    // rustpython-parser (LALRPOP)
    let t=Instant::now(); let mut ok1=0;
    for (p,s) in &srcs { if rustpython_parser::ast::Suite::parse(s,p).is_ok(){ok1+=1;} }
    let e1=t.elapsed().as_secs_f64();

    // ruff parser (hand-written)
    let t=Instant::now(); let mut ok2=0;
    for (_,s) in &srcs { if ruff_python_parser::parse_module(s).is_ok(){ok2+=1;} }
    let e2=t.elapsed().as_secs_f64();

    let mb = total_bytes as f64/1e6;
    println!("{} files, {:.1} MB", srcs.len(), mb);
    println!("  rustpython : {:.3}s  {:>6.1} MB/s  ({} ok)", e1, mb/e1, ok1);
    println!("  ruff       : {:.3}s  {:>6.1} MB/s  ({} ok)  => {:.1}x faster parse", e2, mb/e2, ok2, e1/e2);
}
