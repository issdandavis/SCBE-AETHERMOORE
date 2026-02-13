"""Memory Integrity Test Suite for SCBE-AETHERMOORE 3-Zone Memory System.

Enforces:
1. Canon precedence over working memory
2. Zone-specific rules (canon immutable, working excluded from training)
3. Provenance requirements
4. Promotion gate (working → staging requires tests + review)
5. Timeline coherence
6. No canon drift
"""
import json
import pytest
from pathlib import Path
from datetime import datetime
from typing import List, Dict


class MemoryChunk:
    """Represents a memory chunk conforming to memory_schema.json."""
    def __init__(self, data: Dict):
        self.data = data
        self.id = data['id']
        self.zone = data['zone']
        self.canon = data['canon']
        self.type = data['type']
        self.source = data['source']
        self.training_use = data.get('training_use')
        self.retrieval_priority = data.get('retrieval_priority')
        self.provenance = data['provenance']


def load_memory_chunks(zone: str) -> List[MemoryChunk]:
    """Load all memory chunks from a specific zone."""
    zone_dir = Path(__file__).parent.parent / 'memory' / zone
    chunks = []
    for jsonl_file in zone_dir.rglob('*.jsonl'):
        with open(jsonl_file) as f:
            for line in f:
                if line.strip():
                    chunks.append(MemoryChunk(json.loads(line)))
    return chunks


def load_all_memory() -> Dict[str, List[MemoryChunk]]:
    """Load chunks from all zones."""
    return {
        'canon': load_memory_chunks('canon'),
        'working': load_memory_chunks('working'),
        'staging': load_memory_chunks('staging')
    }


class TestZoneRules:
    """Test zone-specific enforcement rules."""

    def test_canon_zone_immutability(self):
        """Canon zone chunks must be marked canon=True."""
        canon_chunks = load_memory_chunks('canon')
        for chunk in canon_chunks:
            assert chunk.canon is True, f"Canon chunk {chunk.id} must have canon=True"

    def test_canon_zone_priority(self):
        """Canon zone chunks must have retrieval_priority=1."""
        canon_chunks = load_memory_chunks('canon')
        for chunk in canon_chunks:
            assert chunk.retrieval_priority == 1, f"Canon chunk {chunk.id} must have priority 1"

    def test_working_zone_non_canon(self):
        """Working zone chunks must be marked canon=False."""
        working_chunks = load_memory_chunks('working')
        for chunk in working_chunks:
            assert chunk.canon is False, f"Working chunk {chunk.id} must have canon=False"

    def test_working_zone_excluded_from_training(self):
        """Working zone chunks must be excluded from training."""
        working_chunks = load_memory_chunks('working')
        for chunk in working_chunks:
            assert chunk.training_use == 'excluded', \
                f"Working chunk {chunk.id} must have training_use='excluded'"

    def test_working_zone_priority(self):
        """Working zone chunks must have retrieval_priority=3 (lowest)."""
        working_chunks = load_memory_chunks('working')
        for chunk in working_chunks:
            assert chunk.retrieval_priority == 3, f"Working chunk {chunk.id} must have priority 3"

    def test_staging_zone_training_use(self):
        """Staging zone chunks must be marked finetune_ok or eval_only."""
        staging_chunks = load_memory_chunks('staging')
        for chunk in staging_chunks:
            assert chunk.training_use in ('finetune_ok', 'eval_only'), \
                f"Staging chunk {chunk.id} must have training_use in [finetune_ok, eval_only]"

    def test_staging_zone_priority(self):
        """Staging zone chunks must have retrieval_priority=2."""
        staging_chunks = load_memory_chunks('staging')
        for chunk in staging_chunks:
            assert chunk.retrieval_priority == 2, f"Staging chunk {chunk.id} must have priority 2"


class TestProvenance:
    """Test provenance and traceability."""

    def test_all_chunks_have_provenance(self):
        """Every chunk must have provenance."""
        memory = load_all_memory()
        for zone, chunks in memory.items():
            for chunk in chunks:
                assert chunk.provenance is not None, \
                    f"{zone} chunk {chunk.id} missing provenance"
                assert 'author' in chunk.provenance
                assert 'created_at' in chunk.provenance
                assert 'version' in chunk.provenance

    def test_staging_promotion_tracking(self):
        """Staging chunks promoted from working must have promotion_pr."""
        staging_chunks = load_memory_chunks('staging')
        for chunk in staging_chunks:
            if chunk.source == 'promoted':
                assert 'promotion_pr' in chunk.provenance, \
                    f"Promoted chunk {chunk.id} must have promotion_pr in provenance"

    def test_notion_chunks_have_page_id(self):
        """Chunks from Notion must have notion_page_id."""
        memory = load_all_memory()
        for zone, chunks in memory.items():
            for chunk in chunks:
                if chunk.source == 'notion':
                    assert 'notion_page_id' in chunk.provenance, \
                        f"{zone} chunk {chunk.id} from Notion missing notion_page_id"


class TestCanonPrecedence:
    """Test RAG retrieval priority enforcement."""

    def test_no_duplicate_ids_across_zones(self):
        """Same ID must not exist in multiple zones (prevents canon shadow copies)."""
        memory = load_all_memory()
        all_ids = {}
        for zone, chunks in memory.items():
            for chunk in chunks:
                assert chunk.id not in all_ids, \
                    f"Duplicate ID {chunk.id} found in {zone} and {all_ids[chunk.id]}"
                all_ids[chunk.id] = zone

    def test_retrieval_priority_order(self):
        """Verify priority ordering: canon(1) > staging(2) > working(3)."""
        memory = load_all_memory()
        for zone, expected_priority in [('canon', 1), ('staging', 2), ('working', 3)]:
            for chunk in memory[zone]:
                assert chunk.retrieval_priority == expected_priority, \
                    f"{zone} chunk {chunk.id} has wrong priority {chunk.retrieval_priority}"


class TestRelationshipCoherence:
    """Test relationship and timeline consistency."""

    def test_relationship_targets_exist(self):
        """All relationship target_ids must reference existing chunks."""
        memory = load_all_memory()
        all_ids = {chunk.id for chunks in memory.values() for chunk in chunks}
        for zone, chunks in memory.items():
            for chunk in chunks:
                relationships = chunk.data.get('relationships', [])
                for rel in relationships:
                    target_id = rel['target_id']
                    assert target_id in all_ids, \
                        f"{zone} chunk {chunk.id} references nonexistent {target_id}"

    def test_timeline_ordering(self):
        """Timeline chunks with 'precedes' must not form cycles."""
        memory = load_all_memory()
        timeline_chunks = [c for chunks in memory.values() for c in chunks if c.type == 'timeline']
        graph = {}
        for chunk in timeline_chunks:
            graph[chunk.id] = []
            for rel in chunk.data.get('relationships', []):
                if rel['relation_type'] == 'precedes':
                    graph[chunk.id].append(rel['target_id'])
        # Simple cycle detection
        def has_cycle(node, visited, stack):
            visited.add(node)
            stack.add(node)
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, stack):
                        return True
                elif neighbor in stack:
                    return True
            stack.remove(node)
            return False
        visited = set()
        for node in graph:
            if node not in visited:
                assert not has_cycle(node, visited, set()), f"Timeline cycle detected at {node}"


class TestPromotionGate:
    """Test working → staging promotion rules."""

    def test_no_working_chunks_in_staging(self):
        """Staging must not contain chunks with source='agent' unless promoted."""
        staging_chunks = load_memory_chunks('staging')
        for chunk in staging_chunks:
            if chunk.source == 'agent':
                pytest.fail(f"Staging chunk {chunk.id} has source='agent' without promotion")

    def test_staging_chunks_have_version(self):
        """All staging chunks must have a version tag."""
        staging_chunks = load_memory_chunks('staging')
        for chunk in staging_chunks:
            assert chunk.provenance.get('version'), \
                f"Staging chunk {chunk.id} missing version in provenance"


class TestMemoryIntegrityQueries:
    """Test canonical knowledge queries (hardcoded evaluation)."""

    # These are intentionally hardcoded questions to test retrieval accuracy
    EVAL_QUESTIONS = [
        ("What is Sacred Tongue?", "lore", ["sacred", "tongue", "language"]),
        ("Who is Polly?", "character", ["polly", "character"]),
        ("Describe SCBE Layer 5", "system", ["layer", "5", "security"]),
        ("How does collaboration work?", "relationship", ["collaboration", "relationship"]),
    ]

    def test_retrieval_accuracy_mockbasic(self):
        """Basic check: relevant chunks exist for hardcoded questions."""
        memory = load_all_memory()
        # Combine canon + staging only (working is deprioritized)
        searchable = memory['canon'] + memory['staging']
        for question, expected_type, keywords in self.EVAL_QUESTIONS:
            matches = []
            for chunk in searchable:
                text = (chunk.data['title'] + ' ' + chunk.data['text']).lower()
                if any(kw in text for kw in keywords):
                    matches.append(chunk)
            # This is a basic heuristic test — real RAG would use embeddings
            assert len(matches) > 0, f"No chunks found for '{question}' with keywords {keywords}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
