import hashlib

import pytest

from scripts.apollo import obsidian_vault_sync as G
from scripts.apollo import obsidian_tongue_workspace as W


def test_path_collisions_and_heading_links(tmp_path, monkeypatch):
    for folder in ("A", "B"):
        (tmp_path / folder).mkdir()
        (tmp_path / folder / "Same.md").write_text("# Same\n" + folder)
    (tmp_path / "Home.md").write_text("[[A/Same#Heading|first]] [[B/Same]] [[Same]]")
    monkeypatch.setattr(G, "VAULT_PATH", tmp_path)
    graph = G.build_graph(G.scan_vault(), max_semantic_neighbors=1)
    assert {n["id"] for n in graph["nodes"]} == {"A/Same", "B/Same", "Home"}
    edges = {e["target"]: e for e in graph["edges"] if e["source"] == "Home" and e["explicit_link"]}
    assert edges["A/Same"]["target_exists"]
    assert edges["B/Same"]["target_exists"]
    assert not edges["Same"]["target_exists"]


def test_yaml_tags_and_full_byte_hash(tmp_path, monkeypatch):
    raw = b'---\r\ntags: [security, "math/tensor"]\r\n---\r\n' + b"x" * 5000
    path = tmp_path / "Test.md"
    path.write_bytes(raw)
    monkeypatch.setattr(G, "VAULT_PATH", tmp_path)
    first = G.scan_vault()[0]
    assert set(first.tags) == {"security", "math/tensor"}
    assert first.content_hash == hashlib.sha256(raw).hexdigest()
    path.write_bytes(raw + b"y")
    assert G.scan_vault()[0].content_hash != first.content_hash


def test_keyword_boundaries():
    assert G._keyword_hits("statement decode", ["state", "code"]) == 0
    assert G._keyword_hits("state code", ["state", "code"]) == 2


def test_legacy_encoding_and_narrow_yaml_repair():
    content, encoding = W.decode_note(b"# Session\r\nProtocol\x97Notes\r\n")
    assert encoding == "cp1252" and "Protocol—Notes" in content
    original = "---\ntitle: HYDRA: lane\ntags: [kept]\n---\n# Body\nstista_example: keep this prose\n"
    result = W.decorate("Hydra.md", original)
    assert W.yaml.safe_load(result.split("---")[1])["title"] == "HYDRA: lane"
    assert "stista_example: keep this prose" in result
    assert W.body_fingerprint(original) == W.body_fingerprint(result)
    assert W.decorate("Hydra.md", result) == result


def test_parent_relative_link(tmp_path, monkeypatch):
    (tmp_path / "A").mkdir()
    (tmp_path / "Root.md").write_text("# Root")
    (tmp_path / "A/Child.md").write_text("[[../Root]]")
    monkeypatch.setattr(G, "VAULT_PATH", tmp_path)
    notes = G.scan_vault()
    assert next(n for n in notes if n.name == "Child").outgoing_links == ["Root"]


@pytest.mark.parametrize(
    "content",
    [
        "# A\nOriginal prose.\n",
        '---\ntags: [kept, "custom/tag"]\naliases: [Other]\n---\n# A\nOriginal prose.\n',
        "---\n---\n# Empty frontmatter\n",
    ],
)
def test_decorate_idempotent_preserves_body_and_existing_properties(content):
    result = W.decorate("Math/A.md", content)
    assert W.decorate("Math/A.md", result) == result
    assert W.body_fingerprint(result) == W.body_fingerprint(content)
    assert G.frontmatter_tags(result) == G.frontmatter_tags(content)
    assert result.count("stista_primary:") == 1


def test_explicit_override_survives():
    content = "---\nstista_override: UM\n---\n# Context\nmetadata config\n"
    result = W.decorate("Context.md", content)
    assert 'stista_primary: "UM"' in result
    assert "stista_override: UM" in result


def test_no_generated_tag_feedback(tmp_path, monkeypatch):
    path = tmp_path / "Logic.md"
    content = "# Logic\ncompute algorithm code\n"
    decorated = W.decorate("Logic.md", content)
    path.write_text(decorated)
    monkeypatch.setattr(G, "VAULT_PATH", tmp_path)
    note = G.scan_vault()[0]
    assert note.tongue_profile == W.classify("Logic.md", content)[1]
    assert G.source_content(decorated).find("#tongue/") == -1


def test_source_card_uses_original_evidence(tmp_path, monkeypatch):
    content = "# Security\nsecurity encrypt protect guard risk threat\n"
    evidence = W.classify("Security.md", content)
    _, body = W.card("Collection", tmp_path / "Security.md", content, "abc")
    path = tmp_path / "Card.md"
    path.write_text(W.decorate("Card.md", body, evidence=evidence))
    monkeypatch.setattr(G, "VAULT_PATH", tmp_path)
    assert G.scan_vault()[0].tongue_profile == evidence[1]


def test_backup_restores_exact_bytes_and_noop_has_no_receipt(tmp_path):
    root = tmp_path / "audit"
    root.mkdir()
    path = tmp_path / "note.md"
    original = b"\xef\xbb\xbf# Original\r\n"
    path.write_bytes(original)
    records = []
    W.write_change(root, path, b"new", records)
    assert W.gzip.decompress(W.Path(records[0]["backup"]).read_bytes()) == original
    W.write_change(root, path, b"new", records)
    assert len(records) == 1
    assert len((root / "changes.jsonl").read_text().splitlines()) == 1


def test_semantic_degree_cap_retains_explicit_links(tmp_path, monkeypatch):
    for i in range(8):
        (tmp_path / f"{i}.md").write_text("# Governance\npolicy gate agent route audit\n[[0]]")
    monkeypatch.setattr(G, "VAULT_PATH", tmp_path)
    graph = G.build_graph(G.scan_vault(), max_semantic_neighbors=2)
    degree = W.Counter()
    for edge in graph["edges"]:
        if not edge["explicit_link"]:
            degree.update([edge["source"], edge["target"]])
    assert max(degree.values(), default=0) <= 2
    assert len([e for e in graph["edges"] if e["explicit_link"]]) == 8


def test_bad_metadata_profile_does_not_poison_graph(tmp_path, monkeypatch):
    fields = "\n".join(f"stista_mix_{c.lower()}: .nan" for c in G.TONGUE_ORDER)
    (tmp_path / "Bad.md").write_text(
        "---\nstista_method: keyword-role-heuristic-v2\nstista_primary: UM\n" + fields + "\n---\nmath code"
    )
    monkeypatch.setattr(G, "VAULT_PATH", tmp_path)
    assert all(G.math.isfinite(v) for v in G.scan_vault()[0].tongue_profile.values())
