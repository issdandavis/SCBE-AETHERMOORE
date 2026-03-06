"""
List Obsidian Vaults — Find and catalog all Obsidian vaults on the system.

Maps to: $obsidian-vault-ops
Integrates with: obsidian_byproduct_note.py, HYDRA canvas, cross-talk

Usage:
    python list_obsidian_vaults.py
    python list_obsidian_vaults.py --roots "C:\\Users\\issda\\OneDrive\\Documents"
    python list_obsidian_vaults.py --dump-to "C:\\Users\\issda\\OneDrive\\Documents\\DOCCUMENTS\\A follder\\AI Workspace"
    python list_obsidian_vaults.py --json
"""

import json
import os
from argparse import ArgumentParser
from pathlib import Path
from typing import Any, Dict, List, Optional


def find_obsidian_vaults(root_dirs: Optional[List[str]] = None, max_depth: int = 4) -> List[Dict[str, Any]]:
    """Find Obsidian vaults by looking for .obsidian subdirs."""
    if root_dirs is None:
        home = os.path.expanduser("~")
        root_dirs = [
            home,
            os.path.join(home, "Documents"),
            os.path.join(home, "OneDrive", "Documents"),
        ]

    vaults: List[Dict[str, Any]] = []
    seen: set = set()

    for root in root_dirs:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, _ in os.walk(root):
            # Depth limit
            depth = dirpath.replace(root, "").count(os.sep)
            if depth >= max_depth:
                dirnames.clear()
                continue

            # Skip hidden/system dirs
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in {"node_modules", "__pycache__", ".git"}]

            if ".obsidian" in os.listdir(dirpath):
                vault_path = os.path.abspath(dirpath)
                if vault_path in seen:
                    continue
                seen.add(vault_path)

                name = os.path.basename(vault_path)
                config_path = os.path.join(vault_path, ".obsidian", "app.json")
                note_count = sum(1 for f in Path(vault_path).rglob("*.md"))

                if os.path.exists(config_path):
                    try:
                        with open(config_path, "r", encoding="utf-8") as f:
                            config = json.load(f)
                        name = config.get("vaultName", name)
                    except (json.JSONDecodeError, OSError):
                        pass

                vaults.append({
                    "name": name,
                    "path": vault_path,
                    "note_count": note_count,
                })

    return vaults


def dump_to_note(vaults: List[Dict[str, Any]], output_vault_path: str, note_name: str = "vault_list.md") -> str:
    """Dump vault list to a Markdown note in an Obsidian vault."""
    note_path = os.path.join(output_vault_path, note_name)
    os.makedirs(os.path.dirname(note_path), exist_ok=True)
    with open(note_path, "w", encoding="utf-8") as f:
        f.write("# Obsidian Vaults List\n\n")
        f.write(f"*Scanned: {len(vaults)} vaults*\n\n")
        for v in vaults:
            f.write(f"- **{v['name']}** ({v['note_count']} notes): `{v['path']}`\n")
    return note_path


if __name__ == "__main__":
    parser = ArgumentParser(description="List Obsidian vaults and ops.")
    parser.add_argument("--roots", default=None, help="Comma-separated root dirs to search.")
    parser.add_argument("--dump-to", default=None, help="Vault path to dump Markdown note.")
    parser.add_argument("--json", action="store_true", help="JSON output for HYDRA piping.")
    parser.add_argument("--max-depth", type=int, default=4, help="Max directory depth to search.")
    args = parser.parse_args()

    roots = args.roots.split(",") if args.roots else None
    vaults = find_obsidian_vaults(roots, max_depth=args.max_depth)

    if args.json:
        print(json.dumps(vaults, indent=2))
    else:
        print(f"\nFound {len(vaults)} Obsidian vaults:")
        for v in vaults:
            print(f"  [{v['name']}] {v['note_count']} notes -> {v['path']}")
        print()

    if args.dump_to:
        path = dump_to_note(vaults, args.dump_to)
        print(f"Dumped to {path}")
