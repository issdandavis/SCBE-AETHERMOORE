from __future__ import annotations

from pathlib import Path

import pytest

from src.mempalace import (
    VaultIndex,
    build_axiom_mesh,
    build_buckets,
    build_palace,
    dedup_report,
    find_convergence_zones,
    link_rooms_to_notes,
    room_tongue_profile,
    stats_report,
    tokenize,
    vault_stats,
)
from src.mempalace.vault_link import TONGUE_TO_SPHERE_DIR


@pytest.fixture()
def fake_vault(tmp_path: Path) -> Path:
    root = tmp_path / "vault"
    root.mkdir()
    (root / "_inbox.md").write_text(
        "---\ntags: [scbe, axiom]\n---\n# SCBE Note\nGovernance and harmonic stack.\n",
        encoding="utf-8",
    )
    (root / "dup_a.md").write_text("duplicate content\n", encoding="utf-8")
    (root / "dup_b.md").write_text("duplicate content\n", encoding="utf-8")
    sphere = root / "sphere-grid"
    for tongue, dirname in TONGUE_TO_SPHERE_DIR.items():
        tdir = sphere / dirname
        tdir.mkdir(parents=True)
        (tdir / f"{tongue.lower()}_intro.md").write_text(
            f"# {tongue} tongue anchor note\n", encoding="utf-8"
        )
    quarantine = root / "_quarantine" / "should_be_ignored"
    quarantine.mkdir(parents=True)
    (quarantine / "junk.md").write_text("should not appear\n", encoding="utf-8")
    return root


def test_scan_skips_quarantine(fake_vault: Path):
    idx = VaultIndex(root=fake_vault).scan()
    paths = {p.name for p in idx.records}
    assert "junk.md" not in paths
    assert "_inbox.md" in paths


def test_find_duplicates(fake_vault: Path):
    idx = VaultIndex(root=fake_vault).scan()
    dups = idx.find_duplicates()
    assert any(len(paths) >= 2 for paths in dups.values())
    dup_names = {p.name for paths in dups.values() for p in paths}
    assert "dup_a.md" in dup_names
    assert "dup_b.md" in dup_names
    assert idx.duplicate_count() >= 1


def test_tag_and_tongue_extraction(fake_vault: Path):
    idx = VaultIndex(root=fake_vault).scan()
    inbox = next(p for p in idx.records if p.name == "_inbox.md")
    rec = idx.records[inbox]
    assert "scbe" in rec.tags
    assert "axiom" in rec.tags


def test_link_rooms_to_notes(fake_vault: Path):
    idx = VaultIndex(root=fake_vault).scan()
    palace = build_palace()
    mapping = link_rooms_to_notes(palace, idx)
    assert len(mapping) == len(palace)
    all_rooms_nonempty = [rid for rid, notes in mapping.items() if notes]
    assert len(all_rooms_nonempty) == len(palace)
    sample_notes = mapping[0x00]
    assert any("CA-Compute" in str(p) for p in sample_notes)


def test_link_missing_vault_returns_empty(tmp_path: Path):
    idx = VaultIndex(root=tmp_path / "nonexistent")
    palace = build_palace()
    mapping = link_rooms_to_notes(palace, idx)
    assert len(mapping) == len(palace)
    assert all(notes == [] for notes in mapping.values())


def test_scan_missing_vault_is_safe(tmp_path: Path):
    idx = VaultIndex(root=tmp_path / "nope").scan()
    assert idx.records == {}
    assert idx.find_duplicates() == {}


def test_room_tongue_profile_filters_zero_trits():
    palace = build_palace()
    profile = room_tongue_profile(palace[0x00])
    assert "CA" in profile
    assert all(val != 0 for val in profile.values())


def test_tokenize_removes_stopwords():
    tokens = tokenize("The quick brown fox and the slow bear")
    assert "the" not in tokens
    assert "and" not in tokens
    assert "quick" in tokens
    assert "brown" in tokens


def test_build_buckets_and_axioms(tmp_path: Path):
    root = tmp_path / "mini"
    root.mkdir()
    (root / "scbe_note.md").write_text(
        "harmonic wall poincare axiom governance stack\n", encoding="utf-8"
    )
    (root / "phdm_note.md").write_text(
        "polyhedral axiom governance stack 21d\n", encoding="utf-8"
    )
    (root / "hydra_note.md").write_text(
        "swarm axiom governance stack spine\n", encoding="utf-8"
    )
    (root / "lore_note.md").write_text(
        "spiralverse axiom governance stack aethermoor\n", encoding="utf-8"
    )
    idx = VaultIndex(root=root).scan()
    buckets = build_buckets(idx)
    assert buckets["SCBE"].note_count >= 1
    assert buckets["PHDM"].note_count >= 1
    axioms = find_convergence_zones(buckets, top_k=20, min_buckets=2)
    assert "axiom" in axioms
    assert "governance" in axioms


def test_save_load_roundtrip(fake_vault: Path, tmp_path: Path):
    idx = VaultIndex(root=fake_vault).scan()
    cache = tmp_path / "cache.json"
    idx.save(cache)
    assert cache.exists()
    restored = VaultIndex.load(cache)
    assert set(restored.records.keys()) == set(idx.records.keys())
    assert restored.find_duplicates() == idx.find_duplicates()
    assert restored.by_tongue.keys() == idx.by_tongue.keys()


def test_dedup_report_writes_file(fake_vault: Path, tmp_path: Path):
    idx = VaultIndex(root=fake_vault).scan()
    out = tmp_path / "reports" / "dedup.md"
    path = dedup_report(idx, out)
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "Vault Duplicate Report" in text
    assert "dup_a.md" in text
    assert "Never-delete rule" in text


def test_stats_report_has_tongue_section(fake_vault: Path, tmp_path: Path):
    idx = VaultIndex(root=fake_vault).scan()
    stats = vault_stats(idx)
    assert stats["note_count"] >= 1
    out = tmp_path / "reports" / "stats.md"
    path = stats_report(idx, out)
    text = path.read_text(encoding="utf-8")
    assert "Tongue distribution" in text
    assert "Top tags" in text


def test_build_axiom_mesh_end_to_end(tmp_path: Path):
    root = tmp_path / "mesh"
    root.mkdir()
    (root / "scbe_a.md").write_text(
        "harmonic governance axiom convergence\n", encoding="utf-8"
    )
    (root / "scbe_b.md").write_text(
        "harmonic governance axiom resonance\n", encoding="utf-8"
    )
    (root / "phdm_a.md").write_text(
        "polyhedral governance axiom convergence\n", encoding="utf-8"
    )
    (root / "hydra_a.md").write_text(
        "swarm governance axiom convergence\n", encoding="utf-8"
    )
    idx = VaultIndex(root=root).scan()
    mesh = build_axiom_mesh(idx, convergence_min_buckets=2)
    assert mesh.axioms, "axiom list must not be empty"
    assert mesh.edges, "mesh graph must have at least one edge"
    assert mesh.joint_terms, "bridge joints must rank at least one term"
    assert any("governance" == term for term, _ in mesh.joint_terms)
