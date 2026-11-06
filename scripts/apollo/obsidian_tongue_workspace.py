"""Reversible Obsidian organization and a bounded, local Six Tongues index.

plan inventories sources; apply adds provenance cards, tags and hubs and publishes
the existing semantic-gravity graph. Original prose and source files stay intact.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.apollo import obsidian_vault_sync as G

VAULT = Path("C:/Users/issda/Avalon Files (consolidated)")
OUT = G.ROOT / "artifacts/obsidian_workspace_20260914"
HUB = "03-Resources/Tongue Atlas"
CATALOG = "03-Resources/Source Catalog"
PLUGIN = ".obsidian/plugins/stista-gravity"
COLORS = dict(zip(G.TONGUE_ORDER, ["#64c9b7", "#69b9ee", "#dcab65", "#c497ec", "#e4809c", "#a4cd70"]))
EXCLUDE = {
    ".git",
    ".obsidian",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "System Library",
    "Repository Mirror",
    "dist",
    "build",
    ".trash",
}
DENIED = re.compile(r"credential|password|secret|private.key|api.key|token.dump", re.I)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def text(path: Path) -> str:
    return decode_note(path.read_bytes())[0]


def decode_note(data: bytes) -> tuple[str, str]:
    try:
        return data.decode("utf-8-sig").replace("\r\n", "\n"), "utf-8"
    except UnicodeDecodeError:
        # Old Windows exports can contain CP1252 punctuation. Strict decoding
        # and round-trip equality avoid replacement-character data loss.
        decoded = data.decode("cp1252")
        if decoded.encode("cp1252") != data or "\x00" in decoded:
            raise ValueError("Unrecognized text encoding")
        return decoded.replace("\r\n", "\n"), "cp1252"


def repair_title_yaml(content: str) -> str:
    if not content.startswith("---\n"):
        return content
    end = content.find("\n---", 3)
    if end < 0:
        return content
    head = content[4:end]
    try:
        yaml.safe_load(head)
        return content
    except yaml.YAMLError:
        # Narrow repair for observed exports: title: NAME: description.
        fixed = re.sub(r"^title: ([^\"'\n].*?: .*)$", lambda m: "title: " + json.dumps(m.group(1)), head, flags=re.M)
        yaml.safe_load(fixed)
        return "---\n" + fixed + content[end:]


def walk_md(root: Path, depth: int = 12):
    if not root.is_dir():
        return
    for current, dirs, files in os.walk(root, followlinks=False):
        current = Path(current)
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDE and not (current / d).is_symlink())
        if len(current.relative_to(root).parts) >= depth:
            dirs[:] = []
        for name in sorted(files):
            path = current / name
            if path.suffix.lower() == ".md" and not path.is_symlink():
                yield path


def body_fingerprint(content: str) -> str:
    content = G.source_content(content)
    content = re.sub(r"\A---[ \t]*\n.*?^---[ \t]*(?:\n|$)", "", content, count=1, flags=re.S | re.M)
    return sha(" ".join(content.split()).encode())


def source_files():
    roots = {
        "Original Avalon": Path("C:/Users/issda/Documents/Avalon Files"),
        "Local Vault": Path("C:/dev/ObsidianVault-LOCAL"),
        "SCBE Notes": G.ROOT / "notes",
        "SCBE Docs": G.ROOT / "docs",
        "Idea Vault": Path("C:/dev/idea-vault"),
    }
    for label, root in roots.items():
        for path in walk_md(root):
            yield label, root, path
    # Every project is represented by its entry documents. Do not mirror code,
    # package files, raw conversations, weights, or old experiment directories.
    for project in sorted(Path("C:/dev").iterdir()):
        if not project.is_dir() or project.name.startswith((".", "_")):
            continue
        selected = set()
        for name in ("README.md", "AGENTS.md", "SYSTEM_MAP.md", "HANDOFF.md", "PLAN.md"):
            path = project / name
            if path.is_file():
                selected.add(path)
        for sub in ("docs", "notes"):
            for path in walk_md(project / sub, depth=2):
                if re.search(r"system.map|architecture|overview|canonical|tokenizer", path.name, re.I):
                    selected.add(path)
        for path in sorted(selected):
            yield "Projects", project, path
    for dirname in (
        "context_streams_20260914",
        "clay_launch_20260914_914167",
        "clay_scale_20260914",
        "branch_drafting_20260914",
    ):
        root = Path("C:/dev/tongue-compiler/artifacts") / dirname
        for name in ("HANDOFF.md", "PLAN.md", "RESULTS.md", "SYSTEM_MAP.md", "PIVOT_REVIEW_MAP.md"):
            if (root / name).is_file():
                yield "Clay Current Work", root, root / name


def classify(path: str, content: str):
    content = G.source_content(content)
    name = Path(path).stem
    folder = Path(path).parent.as_posix()
    tags = sorted(set(G.TAG.findall(content)) | set(G.frontmatter_tags(content)))
    headings = G.HEADING.findall(content)
    primary = G.classify_tongue(name, folder, content)
    # An explicit owner override remains independent of generated tags.
    match = re.search(r'^stista_override:\s*[\'"]?(KO|AV|RU|CA|UM|DR)', content, re.M)
    if match:
        primary = match.group(1)
    profile = G.compute_tongue_profile(name, folder, [h[1] for h in headings], tags, content, primary)
    subjects, tasks, relations = G.extract_semantic_labels(name, folder, [h[1] for h in headings], tags, content)
    categories = [key for key in subjects if key in G.SUBJECT_KEYWORDS][:3]
    return primary, profile, categories, tasks, relations


def decorate(path: str, content: str, evidence=None) -> str:
    original = G.MANAGED_SECTION.sub("", content).rstrip() + "\n"
    clean = repair_title_yaml(G.source_content(original))
    primary, profile, categories, _, _ = evidence or classify(path, clean)
    fields = dict(
        stista_primary=primary,
        stista_weight_phi=round(G.TONGUE_PHI_WEIGHTS[primary], 6),
        stista_mass_phi=G.compute_semantic_mass(profile),
        stista_method="keyword-role-heuristic-v2",
    )
    fields.update({f"stista_mix_{code.lower()}": value for code, value in profile.items()})
    props = "".join(f"{key}: {json.dumps(value)}\n" for key, value in fields.items())
    if clean.startswith("---\n"):
        end = clean.find("\n---", 3)
        if end < 0:
            raise ValueError("Unclosed YAML frontmatter")
        parsed = yaml.safe_load(clean[4:end])
        if parsed is not None and not isinstance(parsed, dict):
            raise ValueError("Non-mapping frontmatter")
        clean = clean[:end] + "\n" + props.rstrip() + clean[end:]
    else:
        clean = "---\n" + props + "---\n\n" + clean
    tags = [f"#tongue/{primary.lower()}"] + [f"#topic/{key}" for key in categories]
    tags += [f"#tongue-related/{code.lower()}" for code, value in profile.items() if code != primary and value >= 0.15]
    links = [f"[[{HUB}/Tongues/{primary}|{G.TONGUE_FULL_NAMES[primary]}]]"]
    links += [f"[[{HUB}/Topics/{key}|{key}]]" for key in categories]
    return (
        clean.rstrip()
        + "\n\n<!-- stista-index:start -->\n"
        + " ".join(tags)
        + "\n\nTongue/topic index: "
        + " · ".join(links)
        + "\n<!-- stista-index:end -->\n"
    )


def card(label: str, source: Path, content: str, digest: str) -> tuple[str, str]:
    address = sha(str(source.resolve()).casefold().encode())[:12]
    safe_name = re.sub(r"[^\w .-]", "-", source.stem)[:80].rstrip(" .") or "Source"
    path = f"{CATALOG}/{label}/{safe_name} {address}.md"
    headings = [h[1] for h in G.HEADING.findall(G.source_content(content))[:8]]
    body = (
        "---\ntype: source-reference\ntags: [source-reference]\n"
        + f"source_path: {json.dumps(str(source))}\nsource_sha256: {digest}\n---\n\n"
        + f"# {source.stem}\n\n[Open original]({source.as_uri()})\n\n"
        + f"Collection: {label}. This is a reference to an existing document; "
        + "its claims retain the authority of that source. Training admission is separate.\n\n"
        + "## Source headings\n"
        + "\n".join("- " + h for h in headings)
        + "\n"
    )
    return path, body


def prepare(vault: Path):
    desired = {}
    skipped = []
    originals = {}
    fingerprints = set()
    existing_ids = defaultdict(list)
    sources = []
    repairs = []
    for path in walk_md(vault):
        rel = path.relative_to(vault).as_posix()
        if rel.startswith((HUB + "/", CATALOG + "/")):
            continue
        data = path.read_bytes()
        try:
            content, encoding = decode_note(data)
            repaired = repair_title_yaml(content)
            if encoding != "utf-8" or repaired != content:
                repairs.append(dict(path=rel, encoding=encoding, yaml_title_repaired=repaired != content))
            content = repaired
            originals[rel] = data
            fingerprint = body_fingerprint(content)
            fingerprints.add(fingerprint)
            existing_ids[fingerprint].append(rel)
            if len(data) > 2_000_000:
                skipped.append(dict(path=rel, reason="large original retained without rewrite"))
                continue
            desired[rel] = decorate(rel, content)
        except (UnicodeError, ValueError, yaml.YAMLError) as error:
            skipped.append(dict(path=rel, reason=type(error).__name__))
    seen = set()
    for label, root, path in source_files():
        if path in seen:
            continue
        seen.add(path)
        if DENIED.search(path.name):
            skipped.append(dict(path=str(path), reason="credential-shaped filename excluded"))
            continue
        stat = path.stat()
        # Never hydrate OneDrive placeholders as an incidental inventory action.
        if getattr(stat, "st_file_attributes", 0) & 0x400000:
            skipped.append(dict(path=str(path), reason="cloud-only source not hydrated"))
            continue
        if stat.st_size > 2_000_000:
            skipped.append(dict(path=str(path), reason="large source cataloged by location only"))
            sources.append(dict(path=str(path), bytes=stat.st_size, status="large-source-location"))
            continue
        try:
            data = path.read_bytes()
            content, encoding = decode_note(data)
        except (OSError, UnicodeError):
            skipped.append(dict(path=str(path), reason="unreadable source"))
            continue
        fingerprint = body_fingerprint(content)
        record = dict(path=str(path), collection=label, sha256=sha(data), bytes=len(data))
        if fingerprint in fingerprints:
            record.update(status="already-represented", matches=existing_ids.get(fingerprint, []))
        else:
            rel, body = card(label, path, content, sha(data))
            # Classify from the original evidence, not only its reference card.
            evidence = classify(str(path.relative_to(root)), content)
            primary, profile, categories, _, _ = evidence
            desired[rel] = decorate(rel, body, evidence=evidence)
            record.update(
                status="source-reference", vault_path=rel, evidence_profile=profile, evidence_categories=categories
            )
            fingerprints.add(fingerprint)
            existing_ids[fingerprint].append(rel)
        sources.append(record)
    # Hubs are navigational indexes. They are not independent evidence or papers.
    groups = defaultdict(list)
    for rel, content in desired.items():
        for code in re.findall(r"#tongue/(ko|av|ru|ca|um|dr)\b", content):
            groups["Tongues/" + code.upper()].append(rel)
        for topic in re.findall(r"#topic/([a-z-]+)", content):
            groups["Topics/" + topic].append(rel)
    for code in G.TONGUE_ORDER:
        groups.setdefault("Tongues/" + code, [])
    for group, members in sorted(groups.items()):
        title = group.split("/")[-1]
        header = f"---\ntype: navigation-hub\ntags: [navigation-hub]\n---\n\n# {title}\n\n"
        if title in G.TONGUE_ORDER:
            header += (
                f"{G.TONGUE_FULL_NAMES[title]} · φ weight {G.TONGUE_PHI_WEIGHTS[title]:.6f} "
                + f"· phase {G.TONGUE_SECTORS_DEGREES[title]:g}°.\n\n"
                + "Membership is an editable topic-role heuristic, not a measured neural embedding.\n\n"
            )
        desired[f"{HUB}/{group}.md"] = (
            header
            + f"{len(members)} indexed notes.\n\n"
            + "\n".join(f"- [[{Path(rel).with_suffix('').as_posix()}|{Path(rel).stem}]]" for rel in sorted(members))
            + "\n"
        )
    desired[f"{HUB}/Start Here.md"] = (
        "---\ntype: navigation-hub\ntags: [navigation-hub]\n---\n\n# Tongue Atlas\n\n"
        "Open the ribbon compass or command **STISTA gravity: Open Tongue Gravity**. "
        "Search a subject, choose a tongue, then select a node to read its source and six-way mix.\n\n"
        "The standard graph uses tongue tag colors. The custom view uses φ-weighted "
        "attraction to six sector anchors plus explicit/semantic link forces. Toggle φ weights "
        "to compare with equal weighting. It starts paused to leave compute for Clay.\n\n"
        "## Tongues\n"
        + "\n".join(f"- [[{HUB}/Tongues/{code}|{code} — {G.TONGUE_FULL_NAMES[code]}]]" for code in G.TONGUE_ORDER)
        + "\n\n## Topics\n"
        + "\n".join(f"- [[{HUB}/{g}|{g.split('/')[-1]}]]" for g in sorted(groups) if g.startswith("Topics/"))
        + "\n\n## Interpretation\nProfiles are keyword-role estimates. SS1 weights/phases are copied "
        "from src/tokenizer/ss1.ts, profile ss1_transport_v2_1. Six encodings remain derived views "
        "of the same bytes; graph proximity does not prove similarity, truth, security, or learning. "
        "A larger φ weight does not mean a more important or better note. Source references retain originals.\n\n"
        "Use stista_override: KO (or AV/RU/CA/UM/DR) to correct a primary role. "
        "Refresh the database with the maintenance command documented in the audit handoff.\n"
    )
    home = desired.get("Home.md", "# Home\n")
    if "[[03-Resources/Tongue Atlas/Start Here" not in home:
        home = home.replace(
            "# 🏠 Avalon Files — Home",
            "# 🏠 Avalon Files — Home\n\n"
            + f"**[[{HUB}/Start Here|Open the Tongue Atlas and current project index]]**",
        )
        if f"[[{HUB}/Start Here" not in home:
            home += f"\n[[{HUB}/Start Here|Open the Tongue Atlas]]\n"
    desired["Home.md"] = home
    return desired, dict(
        sources=sources,
        repairs=repairs,
        skipped=skipped,
        duplicate_groups=[v for v in existing_ids.values() if len(v) > 1],
        original_notes=len(originals),
        indexed_groups={k: len(v) for k, v in groups.items()},
    )


def write_change(root: Path, path: Path, data: bytes, receipts: list, expected_sha256="unchecked"):
    observed = sha(path.read_bytes()) if path.exists() else None
    if expected_sha256 != "unchecked" and observed != expected_sha256:
        raise RuntimeError("File changed after plan: " + str(path))
    if path.exists() and path.read_bytes() == data:
        return
    before = path.read_bytes() if path.exists() else None
    digest = sha(before) if before is not None else None
    backup = None
    if before is not None:
        backup = root / "backups" / (digest + ".gz")
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            backup.write_bytes(gzip.compress(before, mtime=0))
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".stista-tmp")
    with temp.open("xb") as stream:
        stream.write(data)
    if (path.read_bytes() if path.exists() else None) != before:
        raise RuntimeError("File changed during update: " + str(path))
    os.replace(temp, path)
    entry = dict(
        path=str(path),
        before_sha256=digest,
        after_sha256=sha(data),
        backup=str(backup) if backup else None,
        bytes=len(data),
    )
    receipts.append(entry)
    with (root / "changes.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(entry) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["plan", "apply"])
    parser.add_argument("--vault", type=Path, default=VAULT)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    desired, report = prepare(args.vault)
    proposed = [
        dict(
            path=rel,
            before_sha256=sha((args.vault / rel).read_bytes()) if (args.vault / rel).exists() else None,
            after_sha256=sha(body.encode()),
            bytes=len(body.encode()),
        )
        for rel, body in sorted(desired.items())
    ]
    plan = dict(schema="obsidian.tongue-workspace.v1", vault=str(args.vault), files=proposed, report=report)
    if args.command == "plan":
        (args.out / "PLAN.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
        print(
            json.dumps(
                dict(
                    notes_before=report["original_notes"],
                    planned_notes=len(desired),
                    sources=len(report["sources"]),
                    skipped=len(report["skipped"]),
                    statuses=dict(Counter(row["status"] for row in report["sources"])),
                    bytes_after=sum(row["bytes"] for row in proposed),
                )
            )
        )
        return
    prior = json.loads((args.out / "PLAN.json").read_text(encoding="utf-8"))
    if prior != plan:
        raise RuntimeError("Plan/source changed; review a fresh plan before applying")
    receipts = []
    expected = {row["path"]: row["before_sha256"] for row in proposed}
    for rel, body in sorted(desired.items()):
        path = (args.vault / rel).resolve()
        if not path.is_relative_to(args.vault.resolve()):
            raise ValueError("Note path escaped vault")
        write_change(args.out, path, body.encode(), receipts, expected_sha256=expected[rel])
    graph_path = args.vault / ".obsidian/graph.json"
    graph_config = json.loads(graph_path.read_text()) if graph_path.exists() else {}
    groups = [
        dict(query=f"tag:#tongue/{code.lower()}", color=dict(a=1, rgb=int(color[1:], 16)))
        for code, color in COLORS.items()
    ]
    existing = [
        g
        for g in graph_config.get("colorGroups", [])
        if g.get("query") and not g.get("query", "").startswith("tag:#tongue/")
    ]
    graph_config.update(
        colorGroups=groups + existing,
        showTags=False,
        hideUnresolved=True,
        showOrphans=True,
        textFadeMultiplier=0,
        nodeSizeMultiplier=1,
        lineSizeMultiplier=0.7,
        centerStrength=0.35,
        linkStrength=0.6,
        linkDistance=160,
    )
    write_change(args.out, graph_path, json.dumps(graph_config, indent=2).encode(), receipts)
    G.VAULT_PATH = args.vault
    notes = G.scan_vault()
    graph = G.build_graph(notes, max_semantic_neighbors=6)
    graph.update(
        schema="obsidian.tongue-gravity.v2",
        vault=str(args.vault),
        generated_epoch=time.time(),
        taxonomy="keyword-role-heuristic-v2",
        colors=COLORS,
        semantic_neighbor_cap=6,
        authority=dict(
            profile="ss1_transport_v2_1",
            source=str(G.ROOT / "src/tokenizer/ss1.ts"),
            sha256=sha((G.ROOT / "src/tokenizer/ss1.ts").read_bytes()),
        ),
    )
    encoded = json.dumps(graph, separators=(",", ":")).encode()
    write_change(args.out, args.vault / PLUGIN / "graph.json", encoded, receipts)
    write_change(args.out, G.GRAPH_OUTPUT, encoded, receipts)
    plugin_sources = G.ROOT / "plugins/obsidian-stista-gravity"
    for name in ("main.js", "graph-view.js", "manifest.json", "styles.css"):
        write_change(args.out, args.vault / PLUGIN / name, (plugin_sources / name).read_bytes(), receipts)
    enabled_path = args.vault / ".obsidian/community-plugins.json"
    enabled = json.loads(enabled_path.read_text()) if enabled_path.exists() else []
    if "stista-gravity" not in enabled:
        enabled.append("stista-gravity")
    write_change(args.out, enabled_path, json.dumps(enabled, indent=2).encode(), receipts)
    report.update(
        graph_stats=graph["stats"],
        changes=len(receipts),
        graph_bytes=len(encoded),
        tag_counts=dict(Counter(n.tongue for n in notes)),
        source_copies=0,
        training_admission=False,
        scope_limit=(
            "Local vaults, SCBE notes/docs, all C:/dev project entry maps, "
            "selected current Clay results. Cloud-only archives not recursively hydrated."
        ),
    )
    (args.out / "RESULT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            dict(
                status="APPLIED",
                notes=len(notes),
                changes=len(receipts),
                graph_bytes=len(encoded),
                semantic_links=graph["stats"]["semantic_links"],
            )
        )
    )


if __name__ == "__main__":
    main()
