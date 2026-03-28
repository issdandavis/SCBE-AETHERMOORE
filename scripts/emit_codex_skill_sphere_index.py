import argparse
import datetime as dt
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(md: str) -> dict[str, str]:
    m = FRONTMATTER_RE.match(md)
    if not m:
        return {}
    body = m.group(1)
    out: dict[str, str] = {}
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = k.strip()
        v = v.strip()
        if v.startswith('"') and v.endswith('"'):
            v = v[1:-1]
        if v.startswith("'") and v.endswith("'"):
            v = v[1:-1]
        out[k] = v
    return out


@dataclass(frozen=True)
class Sphere:
    tongue: str
    tier: int
    name: str
    sphere_md: Path
    link: str  # Obsidian wikilink target


@dataclass
class Candidate:
    tongue: str
    tier: int
    score: float
    hits: list[str]


def default_skills_dir() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser().resolve() / "skills"
    # windows default
    home = Path.home()
    return (home / ".codex" / "skills").resolve()


def build_spheres(sphere_root: Path) -> dict[tuple[str, int], Sphere]:
    spheres: dict[tuple[str, int], Sphere] = {}
    for p in sphere_root.rglob("_sphere.md"):
        try:
            md = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        fm = parse_frontmatter(md)
        if fm.get("type") != "skill-sphere":
            continue
        tongue = (fm.get("tongue") or "").strip().upper()
        tier_s = (fm.get("tier") or "").strip()
        name = (fm.get("name") or "").strip()
        if not tongue or not tier_s or not name:
            continue
        try:
            tier = int(tier_s)
        except ValueError:
            continue
        rel = p.relative_to(sphere_root).as_posix()
        # Obsidian uses / paths in wikilinks
        link = rel.replace(".md", "")
        spheres[(tongue, tier)] = Sphere(tongue=tongue, tier=tier, name=name, sphere_md=p, link=link)
    return spheres


def score_keywords(text: str, keywords: dict[str, float]) -> tuple[float, list[str]]:
    # Token-based matching avoids substring false-positives (e.g. "research" containing "search").
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    token_set = set(tokens)
    joined = " ".join(tokens)

    score = 0.0
    hits: list[str] = []
    for raw_kw, w in keywords.items():
        kw = raw_kw.lower().strip()
        kw_tokens = re.findall(r"[a-z0-9]+", kw)
        if not kw_tokens:
            continue
        if len(kw_tokens) == 1:
            if kw_tokens[0] in token_set:
                score += w
                hits.append(raw_kw)
        else:
            phrase = " ".join(kw_tokens)
            if phrase in joined:
                score += w
                hits.append(raw_kw)
    return score, hits


def sphere_rules() -> dict[tuple[str, int], dict[str, float]]:
    # Cheap, robust heuristics: substring matching against skill name + description.
    return {
        # AV Transport
        ("AV", 1): {
            "search": 3.0,
            "query": 2.0,
            "arxiv": 4.0,
            "semrush": 4.0,
            "keyword": 2.0,
        },
        ("AV", 2): {
            "navigate": 4.0,
            "navigation": 4.0,
            "browser": 3.0,
            "playwright": 4.0,
            "playwriter": 4.0,
            "github nav": 4.0,
            "route": 2.0,
        },
        ("AV", 3): {
            "site map": 4.0,
            "sitemap": 4.0,
            "crawl": 4.0,
            "scrape": 3.0,
            "extract": 2.0,
            "map full": 3.0,
        },
        ("AV", 4): {
            "sync": 4.0,
            "mirror": 4.0,
            "connector": 3.0,
            "mcp": 3.0,
            "transport": 3.0,
            "handoff": 2.0,
            "pipeline": 2.0,
        },
        # KO Command
        ("KO", 1): {
            "dispatch": 4.0,
            "route tasks": 4.0,
            "triage": 3.0,
            "assign": 2.0,
            "review comments": 3.0,
        },
        ("KO", 2): {
            "formation": 4.0,
            "swap": 2.0,
            "reorgan": 2.0,
        },
        ("KO", 3): {
            "coordination": 4.0,
            "overwatch": 4.0,
            "relay": 3.0,
            "orchestrator": 3.0,
        },
        ("KO", 4): {
            "admin": 3.0,
            "autopilot": 3.0,
            "universal": 2.0,
            "sovereign": 4.0,
            "compose multiple": 4.0,
            "execution stack": 3.0,
        },
        # RU Entropy
        ("RU", 1): {
            "hypothesis": 4.0,
            "proposal": 3.0,
            "idea": 2.0,
            "experiment": 3.0,
        },
        ("RU", 2): {
            "dataset": 4.0,
            "collect": 3.0,
            "ingest": 3.0,
            "curate": 3.0,
            "notion": 2.0,
            "obsidian": 2.0,
            "research extraction": 3.0,
        },
        ("RU", 3): {
            "chaos": 4.0,
            "fuzz": 4.0,
            "red-team": 3.0,
            "adversarial": 3.0,
            "stress-test": 3.0,
        },
        ("RU", 4): {
            "predict": 4.0,
            "forecast": 3.0,
            "oracle": 4.0,
            "anomaly": 3.0,
        },
        # CA Compute
        ("CA", 1): {
            "code": 2.0,
            "implement": 3.0,
            "frontend": 3.0,
            "game": 3.0,
            "build": 2.0,
        },
        ("CA", 2): {
            "test": 2.0,
            "pytest": 4.0,
            "vitest": 4.0,
            "hypothesis": 3.0,
            "regression": 2.0,
        },
        ("CA", 3): {
            "train": 3.0,
            "fine-tune": 4.0,
            "qlora": 4.0,
            "trl": 4.0,
            "colab": 3.0,
            "sft": 3.0,
            "dpo": 3.0,
        },
        ("CA", 4): {
            "deploy": 3.0,
            "docker": 3.0,
            "k8s": 4.0,
            "vercel": 4.0,
            "server": 2.0,
            "api": 2.0,
        },
        # UM Security
        ("UM", 1): {
            "govern": 3.0,
            "policy": 3.0,
            "compliance": 3.0,
            "scan": 3.0,
        },
        ("UM", 2): {
            "threat": 4.0,
            "attack": 3.0,
            "mitre": 3.0,
            "atlas": 3.0,
            "vulnerability": 3.0,
        },
        ("UM", 3): {
            "audit": 4.0,
            "trail": 4.0,
            "ledger": 3.0,
            "evidence": 2.0,
            "hash chain": 3.0,
        },
        ("UM", 4): {
            "seal": 4.0,
            "signature": 3.0,
            "crypto": 3.0,
            "pq": 3.0,
            "ml-dsa": 4.0,
        },
        # DR Structure
        ("DR", 1): {
            "docs": 3.0,
            "documentation": 4.0,
            "manual": 2.0,
            "write": 1.5,
        },
        ("DR", 2): {
            "debug": 4.0,
            "fix": 2.0,
            "ci": 3.0,
            "lint": 3.0,
            "failing": 2.0,
        },
        ("DR", 3): {
            "self-heal": 4.0,
            "doctor": 3.0,
            "health check": 3.0,
            "recover": 3.0,
            "watchdog": 3.0,
            "cultivation": 2.0,
        },
        ("DR", 4): {
            "architecture": 4.0,
            "system": 2.0,
            "design": 2.0,
            "module": 2.0,
            "map": 2.0,
        },
    }


def classify_skill(name: str, description: str, spheres: dict[tuple[str, int], Sphere]) -> tuple[Sphere, list[Candidate]]:
    text = f"{name} {description}".lower()
    # normalize separators
    text = text.replace("_", " ").replace("-", " ")

    rules = sphere_rules()
    candidates: list[Candidate] = []
    for key, kw in rules.items():
        tongue, tier = key
        if (tongue, tier) not in spheres:
            continue
        s, hits = score_keywords(text, kw)
        candidates.append(Candidate(tongue=tongue, tier=tier, score=s, hits=hits))

    # fallback bias: if nothing hit, gently default to DR documentation
    candidates.sort(key=lambda c: c.score, reverse=True)
    top = candidates[0] if candidates else Candidate(tongue="DR", tier=1, score=0.0, hits=[])
    if top.score <= 0.0:
        return spheres.get(("DR", 1), next(iter(spheres.values()))), candidates[:5]

    return spheres[(top.tongue, top.tier)], candidates[:5]


def read_skill_meta(skill_dir: Path) -> tuple[str, str]:
    md_path = skill_dir / "SKILL.md"
    if not md_path.exists():
        return skill_dir.name, ""
    md = md_path.read_text(encoding="utf-8", errors="replace")
    fm = parse_frontmatter(md)
    name = (fm.get("name") or "").strip() or skill_dir.name
    desc = (fm.get("description") or "").strip()
    return name, desc


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit Codex skill -> sphere-grid index (md + json).")
    ap.add_argument("--skills-dir", default="", help="Codex skills dir (defaults to ~/.codex/skills or CODEX_HOME).")
    ap.add_argument("--sphere-root", default="notes/sphere-grid", help="Sphere-grid root inside repo.")
    ap.add_argument("--out-md", default="notes/sphere-grid/codex_skill_sphere_index.md")
    ap.add_argument("--out-json", default="notes/sphere-grid/codex_skill_sphere_index.json")
    ap.add_argument("--top-candidates", type=int, default=3)
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    sphere_root = (repo_root / args.sphere_root).resolve()
    if not sphere_root.exists():
        raise SystemExit(f"Sphere root not found: {sphere_root}")

    skills_dir = Path(args.skills_dir).expanduser().resolve() if args.skills_dir else default_skills_dir()
    if not skills_dir.exists():
        raise SystemExit(f"Skills dir not found: {skills_dir}")

    spheres = build_spheres(sphere_root)
    if not spheres:
        raise SystemExit(f"No skill spheres found under: {sphere_root}")

    items: list[dict[str, Any]] = []
    # Skills can be nested (e.g. `.system/openai-docs`). Index any directory
    # that contains a SKILL.md file, not just top-level folders.
    skill_dirs: list[Path] = []
    for md in skills_dir.rglob("SKILL.md"):
        skill_dirs.append(md.parent)

    # Deterministic order by relative path inside the skills dir.
    def rel_key(p: Path) -> str:
        try:
            return p.relative_to(skills_dir).as_posix().lower()
        except Exception:
            return p.as_posix().lower()

    for d in sorted(skill_dirs, key=rel_key):
        name, desc = read_skill_meta(d)
        primary, cand = classify_skill(name, desc, spheres)
        try:
            skill_rel = d.relative_to(skills_dir).as_posix()
        except Exception:
            skill_rel = d.name
        items.append(
            {
                "skill": name,
                "skill_dir": skill_rel,
                "description": desc,
                "primary": {
                    "tongue": primary.tongue,
                    "tier": primary.tier,
                    "sphere_name": primary.name,
                    "sphere_path": str(primary.sphere_md),
                    "sphere_link": primary.link,
                },
                "candidates": [
                    {"tongue": c.tongue, "tier": c.tier, "score": c.score, "hits": c.hits[:10]}
                    for c in cand[: max(1, args.top_candidates)]
                ],
            }
        )

    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "generated_at_utc": now.isoformat(),
        "repo_root": str(repo_root),
        "sphere_root": str(sphere_root),
        "skills_dir": str(skills_dir),
        "count": len(items),
        "items": items,
    }

    out_json = (repo_root / args.out_json).resolve()
    out_md = (repo_root / args.out_md).resolve()
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines: list[str] = []
    lines.append("# Codex Skill -> Sphere Index")
    lines.append("")
    lines.append(f"Generated: {payload['generated_at_utc']}")
    lines.append(f"Skills dir: `{payload['skills_dir']}`")
    lines.append("")
    lines.append("| Skill | Primary sphere | Skill dir |")
    lines.append("|---|---|---|")
    for it in sorted(items, key=lambda x: (x["primary"]["tongue"], x["primary"]["tier"], x["skill"].lower())):
        sph = it["primary"]
        link = f"[[{sph['sphere_link']}|{sph['tongue']} T{sph['tier']} {sph['sphere_name']}]]"
        lines.append(f"| `{it['skill']}` | {link} | `{it['skill_dir']}` |")
    lines.append("")
    lines.append("## Candidates (top)")
    lines.append("")
    for it in sorted(items, key=lambda x: x["skill"].lower()):
        lines.append(f"### {it['skill']}")
        for c in it["candidates"]:
            sph = spheres.get((c["tongue"], c["tier"]))
            if sph is None:
                continue
            hits = ", ".join(c.get("hits") or [])
            lines.append(f"- [[{sph.link}|{c['tongue']} T{c['tier']} {sph.name}]] score={c['score']:.1f} hits={hits}")
        lines.append("")
    out_md.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

    print(str(out_md))
    print(str(out_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
