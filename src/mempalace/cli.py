"""Memory palace + vault CLI.

Read-only on the vault. Caches the index under .scbe/vault_index.json so
re-runs are near-instant. Writes reports into a target directory so you
can review duplicate clusters and lattice stats without touching notes.

    python -m src.mempalace.cli scan   --vault notes --cache .scbe/vault_index.json
    python -m src.mempalace.cli stats  --cache .scbe/vault_index.json --out notes/_reports
    python -m src.mempalace.cli dedup  --cache .scbe/vault_index.json --out notes/_reports
    python -m src.mempalace.cli link   --cache .scbe/vault_index.json
    python -m src.mempalace.cli axioms --cache .scbe/vault_index.json --out notes/_reports
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from src.mempalace.axiom_mesh import build_axiom_mesh
from src.mempalace.rooms import build_palace
from src.mempalace.vault_link import (
    VaultIndex,
    dedup_report,
    link_rooms_to_notes,
    stats_report,
    vault_stats,
)


def _load_or_scan(cache_path: Path, vault_path: Path | None) -> VaultIndex:
    if cache_path.exists():
        return VaultIndex.load(cache_path)
    if vault_path is None:
        raise SystemExit(f"no cache at {cache_path} and no --vault given")
    idx = VaultIndex(root=vault_path).scan()
    idx.save(cache_path)
    return idx


def cmd_scan(args: argparse.Namespace) -> int:
    vault = Path(args.vault).resolve()
    cache = Path(args.cache).resolve()
    if not vault.exists():
        print(f"vault not found: {vault}", file=sys.stderr)
        return 2
    t0 = time.time()
    idx = VaultIndex(root=vault).scan()
    idx.save(cache)
    dt = time.time() - t0
    print(f"scanned {len(idx.records)} notes in {dt:.1f}s -> {cache}")
    print(f"unique hashes: {len(idx.by_hash)}")
    print(f"duplicate clusters: {len(idx.find_duplicates())}")
    print(f"extra copies: {idx.duplicate_count()}")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    cache = Path(args.cache).resolve()
    idx = _load_or_scan(cache, Path(args.vault).resolve() if args.vault else None)
    out_dir = Path(args.out).resolve()
    out_path = stats_report(idx, out_dir / "vault_stats.md")
    stats = vault_stats(idx)
    print(f"stats -> {out_path}")
    print(f"notes: {stats['note_count']}")
    print(f"tongues: {stats['tongue_counts']}")
    return 0


def cmd_dedup(args: argparse.Namespace) -> int:
    cache = Path(args.cache).resolve()
    idx = _load_or_scan(cache, Path(args.vault).resolve() if args.vault else None)
    out_dir = Path(args.out).resolve()
    out_path = dedup_report(idx, out_dir / "vault_dedup.md")
    print(f"dedup report -> {out_path}")
    print(f"clusters: {len(idx.find_duplicates())}, extra copies: {idx.duplicate_count()}")
    return 0


def cmd_link(args: argparse.Namespace) -> int:
    cache = Path(args.cache).resolve()
    idx = _load_or_scan(cache, Path(args.vault).resolve() if args.vault else None)
    palace = build_palace()
    mapping = link_rooms_to_notes(palace, idx)
    nonempty = sum(1 for notes in mapping.values() if notes)
    total = sum(len(notes) for notes in mapping.values())
    print(f"linked {nonempty}/{len(mapping)} rooms to {total} note references")
    if args.sample:
        for rid in list(mapping.keys())[: args.sample]:
            names = [p.name for p in mapping[rid][:3]]
            print(f"  room 0x{rid:02X} {palace[rid].name}: {names}")
    return 0


def cmd_axioms(args: argparse.Namespace) -> int:
    cache = Path(args.cache).resolve()
    idx = _load_or_scan(cache, Path(args.vault).resolve() if args.vault else None)
    mesh = build_axiom_mesh(idx, convergence_min_buckets=args.min_buckets)
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "axiom_mesh.md"
    lines = []
    lines.append("# Axiom Convergence Mesh")
    lines.append("")
    lines.append(f"- Notes indexed: {len(idx.records)}")
    lines.append(f"- Buckets: {len(mesh.buckets)}")
    lines.append(f"- Axioms: {len(mesh.axioms)}")
    lines.append(f"- Mesh edges: {len(mesh.edges)}")
    lines.append(f"- Joint terms: {len(mesh.joint_terms)}")
    lines.append("")
    lines.append("## Buckets")
    lines.append("")
    for name, profile in mesh.buckets.items():
        lines.append(f"- **{name}**: {profile.note_count} notes, " f"{len(profile.term_counts)} distinct terms")
    lines.append("")
    lines.append("## Top axioms (cross-layer invariants)")
    lines.append("")
    for term in mesh.axioms[:60]:
        lines.append(f"- `{term}`")
    lines.append("")
    lines.append("## Bridge joints")
    lines.append("")
    for term, rank in mesh.joint_terms[:40]:
        lines.append(f"- `{term}` — spans {rank} buckets")
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"axiom mesh -> {out_path}")
    print(f"axioms: {len(mesh.axioms)}, joints: {len(mesh.joint_terms)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mempalace", description="SCBE vault + memory palace CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan", help="Scan a vault and cache the index")
    p_scan.add_argument("--vault", required=True)
    p_scan.add_argument("--cache", default=".scbe/vault_index.json")
    p_scan.set_defaults(func=cmd_scan)

    p_stats = sub.add_parser("stats", help="Write a lattice stats report")
    p_stats.add_argument("--cache", default=".scbe/vault_index.json")
    p_stats.add_argument("--vault", default=None)
    p_stats.add_argument("--out", default="notes/_reports")
    p_stats.set_defaults(func=cmd_stats)

    p_dedup = sub.add_parser("dedup", help="Write a duplicate content report (non-destructive)")
    p_dedup.add_argument("--cache", default=".scbe/vault_index.json")
    p_dedup.add_argument("--vault", default=None)
    p_dedup.add_argument("--out", default="notes/_reports")
    p_dedup.set_defaults(func=cmd_dedup)

    p_link = sub.add_parser("link", help="Link memory palace rooms to vault notes")
    p_link.add_argument("--cache", default=".scbe/vault_index.json")
    p_link.add_argument("--vault", default=None)
    p_link.add_argument("--sample", type=int, default=0)
    p_link.set_defaults(func=cmd_link)

    p_ax = sub.add_parser("axioms", help="Build axiom convergence mesh across buckets")
    p_ax.add_argument("--cache", default=".scbe/vault_index.json")
    p_ax.add_argument("--vault", default=None)
    p_ax.add_argument("--out", default="notes/_reports")
    p_ax.add_argument("--min-buckets", type=int, default=2, dest="min_buckets")
    p_ax.set_defaults(func=cmd_axioms)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
