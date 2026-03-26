"""
Tests for hydra.octree_sphere_grid — Signed-Axis Octree + FF10 Sphere Grid + Fractal Chladni.

Covers:
  - Morton encode/decode roundtrip
  - Sign triplet classification
  - Mirror and toroidal wrap
  - SphereSlot and SphereGrid (topology, activation, BFS path)
  - OctreeVoxel creation
  - OctreeNode insertion and collection
  - SignedOctree (insert, octant query, intent query, authority query, Morton range query)
  - Mirror octant operation
  - Cross-branch creation
  - Fractal Chladni mode scaling
  - Interop matrix structure
"""

import math
import pytest

from hydra.octree_sphere_grid import (
    morton_encode_3d,
    morton_decode_3d,
    sign_triplet,
    mirror_point,
    toroidal_wrap,
    SlotType,
    SphereSlot,
    SphereGrid,
    OctreeVoxel,
    OctreeNode,
    SignedOctree,
    CyclicBundle25D,
    AdaptiveQuadtree25D,
    HyperbolicLattice25D,
    OCTANT_NAMES,
    FACE_PLANES,
    INTEROP_MATRIX,
)

# ===================================================================
#  Morton Encode / Decode
# ===================================================================


class TestMortonEncoding:
    def test_roundtrip_origin(self):
        code = morton_encode_3d(0, 0, 0)
        assert morton_decode_3d(code) == (0, 0, 0)

    def test_roundtrip_small(self):
        for x, y, z in [(1, 2, 3), (7, 0, 5), (255, 255, 255)]:
            code = morton_encode_3d(x, y, z)
            assert morton_decode_3d(code) == (x, y, z)

    def test_roundtrip_large(self):
        x, y, z = 1000, 500, 750
        code = morton_encode_3d(x, y, z)
        assert morton_decode_3d(code) == (x, y, z)

    def test_monotonic_x(self):
        """Morton codes increase with x when y,z are fixed."""
        codes = [morton_encode_3d(x, 0, 0) for x in range(10)]
        assert codes == sorted(codes)

    def test_different_inputs_different_codes(self):
        c1 = morton_encode_3d(1, 2, 3)
        c2 = morton_encode_3d(3, 2, 1)
        assert c1 != c2


# ===================================================================
#  Sign Triplet
# ===================================================================


class TestSignTriplet:
    def test_all_positive(self):
        assert sign_triplet(0.5, 0.5, 0.5) == (True, True, True)

    def test_all_negative(self):
        assert sign_triplet(-0.5, -0.5, -0.5) == (False, False, False)

    def test_mixed(self):
        assert sign_triplet(0.5, -0.5, 0.5) == (True, False, True)

    def test_zero_is_positive(self):
        assert sign_triplet(0.0, 0.0, 0.0) == (True, True, True)

    def test_all_eight_octants_mapped(self):
        assert len(OCTANT_NAMES) == 8


# ===================================================================
#  Mirror Point
# ===================================================================


class TestMirrorPoint:
    def test_no_flip(self):
        assert mirror_point(1, 2, 3) == (1, 2, 3)

    def test_flip_x(self):
        assert mirror_point(1, 2, 3, flip_x=True) == (-1, 2, 3)

    def test_flip_all(self):
        assert mirror_point(1, 2, 3, flip_x=True, flip_y=True, flip_z=True) == (-1, -2, -3)

    def test_flip_preserves_magnitude(self):
        mx, my, mz = mirror_point(0.5, -0.3, 0.7, flip_y=True)
        assert abs(mx) == 0.5
        assert abs(my) == 0.3
        assert abs(mz) == 0.7


# ===================================================================
#  Toroidal Wrap
# ===================================================================


class TestToroidalWrap:
    def test_within_bounds(self):
        assert toroidal_wrap(0.5) == 0.5
        assert toroidal_wrap(-0.5) == -0.5

    def test_at_boundary(self):
        assert toroidal_wrap(1.0) == 1.0
        assert toroidal_wrap(-1.0) == -1.0

    def test_wraps_positive_overflow(self):
        result = toroidal_wrap(1.5)
        assert -1.0 <= result <= 1.0

    def test_wraps_negative_overflow(self):
        result = toroidal_wrap(-1.5)
        assert -1.0 <= result <= 1.0

    def test_wrap_symmetry(self):
        # +1.3 and -1.3 should wrap to symmetric positions
        wp = toroidal_wrap(1.3)
        wn = toroidal_wrap(-1.3)
        assert abs(wp + wn) < 1e-10


# ===================================================================
#  SphereSlot
# ===================================================================


class TestSphereSlot:
    def test_defaults(self):
        s = SphereSlot(slot_id=0)
        assert s.slot_type == SlotType.EMPTY
        assert s.activated is False
        assert s.tongue == "KO"

    def test_phi_weight_ko(self):
        s = SphereSlot(slot_id=0, tongue="KO")
        assert abs(s.weight - 1.0) < 1e-6

    def test_phi_weight_dr(self):
        s = SphereSlot(slot_id=0, tongue="DR")
        assert s.weight > 10.0  # DR has highest phi weight


# ===================================================================
#  SphereGrid
# ===================================================================


class TestSphereGrid:
    def test_default_has_10_slots(self):
        g = SphereGrid.create_default()
        assert len(g.slots) == 10

    def test_all_slots_start_inactive(self):
        g = SphereGrid.create_default()
        assert g.activated_count() == 0

    def test_activate_connected_slot(self):
        g = SphereGrid.create_default()
        # slot 0 connects to slot 1 and slot 5
        assert g.activate_slot(1) is True
        assert g.slots[1].activated is True
        assert g.active_slot == 1

    def test_activate_unconnected_slot_fails(self):
        g = SphereGrid.create_default()
        # slot 0 does not connect to slot 9
        assert g.activate_slot(9) is False

    def test_activate_out_of_range_fails(self):
        g = SphereGrid.create_default()
        assert g.activate_slot(-1) is False
        assert g.activate_slot(10) is False

    def test_bfs_path_to_self(self):
        g = SphereGrid.create_default()
        assert g.path_to(0) == [0]

    def test_bfs_path_to_neighbor(self):
        g = SphereGrid.create_default()
        path = g.path_to(1)
        assert path[0] == 0
        assert path[-1] == 1

    def test_bfs_path_to_distant_slot(self):
        g = SphereGrid.create_default()
        path = g.path_to(9)
        assert len(path) >= 2
        assert path[0] == 0
        assert path[-1] == 9

    def test_cross_connections_exist(self):
        g = SphereGrid.create_default()
        # slot 0 should connect to slot 5 (cross row)
        assert 5 in g.slots[0].connections

    def test_to_dict_structure(self):
        g = SphereGrid.create_default()
        d = g.to_dict()
        assert "active_slot" in d
        assert "activated_count" in d
        assert "slots" in d
        assert len(d["slots"]) == 10

    def test_slot_types_cycle(self):
        g = SphereGrid.create_default()
        types = [s.slot_type for s in g.slots]
        assert SlotType.INTENT in types
        assert SlotType.AUTHORITY in types
        assert SlotType.SPECTRAL in types
        assert SlotType.GOVERNANCE in types
        assert SlotType.MERGE in types


# ===================================================================
#  OctreeNode
# ===================================================================


class TestOctreeNode:
    def test_octant_index_all_positive(self):
        node = OctreeNode()
        assert node._octant_index(0.5, 0.5, 0.5) == 7  # 1|2|4

    def test_octant_index_all_negative(self):
        node = OctreeNode()
        assert node._octant_index(-0.5, -0.5, -0.5) == 0

    def test_octant_index_mixed(self):
        node = OctreeNode()
        # x>=0 -> bit 0, y<0, z>=0 -> bit 2
        assert node._octant_index(0.1, -0.1, 0.1) == 5  # 1|0|4

    def test_insert_creates_children(self):
        node = OctreeNode(max_depth=2)
        v = OctreeVoxel(x=0.5, y=0.5, z=0.5, octant=(True, True, True), morton_code=0)
        node.insert(v)
        assert not node.is_leaf

    def test_collect_all_returns_inserted(self):
        node = OctreeNode(max_depth=2)
        v = OctreeVoxel(x=0.5, y=0.5, z=0.5, octant=(True, True, True), morton_code=0)
        node.insert(v)
        assert node.count() == 1

    def test_fractal_chladni_mode_at_depth(self):
        node = OctreeNode(depth=0, chladni_base_mode=(3, 2))
        assert node.chladni_mode == (3, 2)
        deep = OctreeNode(depth=3, chladni_base_mode=(3, 2))
        n, m = deep.chladni_mode
        assert n > 3  # scaled by PHI^3
        assert m > 2

    def test_depth_stats(self):
        node = OctreeNode(max_depth=1)
        v = OctreeVoxel(x=0.5, y=0.5, z=0.5, octant=(True, True, True), morton_code=0)
        node.insert(v)
        stats = node.depth_stats()
        assert 1 in stats
        assert stats[1] == 1


# ===================================================================
#  SignedOctree — Core
# ===================================================================


class TestSignedOctreeInsert:
    def test_insert_returns_voxel(self):
        tree = SignedOctree(max_depth=3)
        v = tree.insert(0.5, 0.5, 0.5, intent_label="test")
        assert v.intent_label == "test"
        assert v.octant == (True, True, True)

    def test_insert_negative_coordinates(self):
        tree = SignedOctree(max_depth=3)
        v = tree.insert(-0.5, -0.5, -0.5)
        assert v.octant == (False, False, False)

    def test_insert_wraps_out_of_bounds(self):
        tree = SignedOctree(max_depth=3)
        v = tree.insert(1.5, 0.0, 0.0)
        assert -1.0 <= v.x <= 1.0

    def test_insert_sets_morton_code(self):
        tree = SignedOctree(max_depth=3)
        v = tree.insert(0.5, 0.5, 0.5)
        assert v.morton_code > 0

    def test_insert_sets_chladni(self):
        tree = SignedOctree(max_depth=3)
        v = tree.insert(0.3, 0.4, 0.1)
        assert isinstance(v.chladni_value, float)

    def test_insert_sets_authority_hash(self):
        tree = SignedOctree(max_depth=3)
        v = tree.insert(0.1, 0.1, 0.1, authority="sealed")
        assert len(v.authority_hash) == 32

    def test_insert_creates_sphere_grid(self):
        tree = SignedOctree(max_depth=3)
        v = tree.insert(0.5, 0.5, 0.5)
        assert len(v.sphere_grid.slots) == 10

    def test_insert_no_sphere_grid(self):
        tree = SignedOctree(max_depth=3)
        v = tree.insert(0.5, 0.5, 0.5, create_sphere_grid=False)
        assert len(v.sphere_grid.slots) == 0


# ===================================================================
#  SignedOctree — Queries
# ===================================================================


class TestSignedOctreeQueries:
    @pytest.fixture
    def populated_tree(self):
        tree = SignedOctree(max_depth=4)
        tree.insert(0.5, 0.5, 0.5, intent_label="a", intent_vector=[1, 0, 0], authority="sealed")
        tree.insert(-0.5, 0.5, 0.5, intent_label="b", intent_vector=[0, 1, 0], authority="public")
        tree.insert(0.5, -0.5, -0.5, intent_label="c", intent_vector=[1, 0, 0], authority="sealed")
        tree.insert(-0.3, -0.3, 0.3, intent_label="d", intent_vector=[0, 0, 1], authority="internal")
        return tree

    def test_query_by_octant(self, populated_tree):
        results = populated_tree.query_by_octant((True, True, True))
        assert len(results) == 1
        assert results[0].intent_label == "a"

    def test_query_by_octant_empty(self, populated_tree):
        results = populated_tree.query_by_octant((True, False, True))
        assert len(results) == 0

    def test_query_by_intent_similar(self, populated_tree):
        results = populated_tree.query_by_intent([1, 0, 0], min_similarity=0.9)
        labels = [v.intent_label for v, _ in results]
        assert "a" in labels
        assert "c" in labels

    def test_query_by_intent_with_octant_filter(self, populated_tree):
        results = populated_tree.query_by_intent([1, 0, 0], octant=(True, True, True), min_similarity=0.5)
        assert len(results) == 1

    def test_query_by_authority(self, populated_tree):
        results = populated_tree.query_by_authority("sealed")
        assert len(results) == 2

    def test_query_by_authority_none(self, populated_tree):
        results = populated_tree.query_by_authority("restricted")
        assert len(results) == 0

    def test_query_by_morton_range(self, populated_tree):
        all_v = populated_tree.root.collect_all()
        mortons = sorted(v.morton_code for v in all_v)
        results = populated_tree.query_by_morton_range(mortons[0], mortons[-1])
        assert len(results) == 4

    def test_collect_all(self, populated_tree):
        assert len(populated_tree.root.collect_all()) == 4


# ===================================================================
#  SignedOctree — Mirror Operations
# ===================================================================


class TestSignedOctreeMirror:
    def test_mirror_creates_voxels(self):
        tree = SignedOctree(max_depth=3)
        tree.insert(0.3, 0.5, 0.7, intent_label="orig")
        mirrored = tree.mirror_octant((True, True, True), (False, False, False))
        assert len(mirrored) == 1
        assert mirrored[0].intent_label == "mirror_orig"

    def test_mirror_flips_coordinates(self):
        tree = SignedOctree(max_depth=3)
        tree.insert(0.3, 0.5, 0.7, intent_label="orig")
        mirrored = tree.mirror_octant((True, True, True), (False, False, False))
        v = mirrored[0]
        assert v.x < 0
        assert v.y < 0
        assert v.z < 0

    def test_mirror_preserves_count(self):
        tree = SignedOctree(max_depth=3)
        tree.insert(0.3, 0.5, 0.7)
        tree.insert(0.1, 0.2, 0.3)
        mirrored = tree.mirror_octant((True, True, True), (False, True, True))
        assert len(mirrored) == 2

    def test_mirror_with_intent_transform(self):
        tree = SignedOctree(max_depth=3)
        tree.insert(0.3, 0.5, 0.7, intent_vector=[1, 0, 0])
        mirrored = tree.mirror_octant((True, True, True), (False, False, False), transform_intent=True)
        # Intent should be negated
        assert mirrored[0].intent_vector[0] < 0

    def test_mirror_stores_metadata(self):
        tree = SignedOctree(max_depth=3)
        tree.insert(0.3, 0.5, 0.7, intent_label="orig")
        mirrored = tree.mirror_octant((True, True, True), (False, False, False))
        assert "_mirrored_from" in mirrored[0].payload


# ===================================================================
#  SignedOctree — Cross-Branch Attachments
# ===================================================================


class TestCrossBranches:
    def test_add_cross_branch(self):
        tree = SignedOctree()
        tree.add_cross_branch("+x+y+z", "+x+y-z", "xy")
        assert len(tree._cross_branches) == 1

    def test_auto_cross_branches_count(self):
        tree = SignedOctree()
        count = tree.auto_cross_branches()
        # 8 octants, each pair differing by 1 axis: C(8, adjacent) = 12
        assert count == 12

    def test_auto_cross_branches_no_duplicates(self):
        tree = SignedOctree()
        tree.auto_cross_branches()
        pairs = [(a, b) for a, b, _ in tree._cross_branches]
        assert len(pairs) == len(set(pairs))


# ===================================================================
#  SignedOctree — Stats
# ===================================================================


class TestSignedOctreeStats:
    def test_empty_stats(self):
        tree = SignedOctree()
        s = tree.stats()
        assert s["count"] == 0

    def test_populated_stats(self):
        tree = SignedOctree(max_depth=3)
        tree.insert(0.5, 0.5, 0.5, tongue="DR", authority="sealed")
        tree.insert(-0.5, -0.5, -0.5, tongue="KO", authority="public")
        tree.auto_cross_branches()
        s = tree.stats()
        assert s["count"] == 2
        assert s["octants_used"] == 2
        assert s["cross_branches"] == 12
        assert s["total_sphere_slots"] == 20
        assert "chladni_range" in s
        assert "morton_range" in s

    def test_stats_authority_distribution(self):
        tree = SignedOctree(max_depth=3)
        tree.insert(0.1, 0.1, 0.1, authority="sealed")
        tree.insert(0.2, 0.2, 0.2, authority="sealed")
        tree.insert(-0.1, -0.1, -0.1, authority="public")
        s = tree.stats()
        assert s["authority_distribution"]["sealed"] == 2
        assert s["authority_distribution"]["public"] == 1


# ===================================================================
#  Face Planes
# ===================================================================


class TestFacePlanes:
    def test_six_face_planes(self):
        assert len(FACE_PLANES) == 6

    def test_plane_names(self):
        names = [name for name, _ in FACE_PLANES]
        assert "xy+" in names
        assert "xy-" in names
        assert "xz+" in names
        assert "yz+" in names


# ===================================================================
#  Interop Matrix
# ===================================================================


class TestInteropMatrix:
    def test_has_concepts(self):
        assert "concepts" in INTEROP_MATRIX
        assert "type_mappings" in INTEROP_MATRIX

    def test_core_concepts_present(self):
        concepts = INTEROP_MATRIX["concepts"]
        for key in [
            "SignedOctree",
            "MortonCode",
            "ChladniAmplitude",
            "SphereGrid",
            "PoincareDistance",
            "ToroidalWrap",
            "IntentSimilarity",
            "AuthorityHash",
        ]:
            assert key in concepts, f"Missing concept: {key}"

    def test_each_concept_has_python(self):
        for name, langs in INTEROP_MATRIX["concepts"].items():
            assert "python" in langs or "formula" in langs, f"{name} missing python entry"

    def test_type_mappings_complete(self):
        mappings = INTEROP_MATRIX["type_mappings"]
        assert "np.ndarray" in mappings
        assert "dataclass" in mappings
        assert "Enum" in mappings


# ===================================================================
#  2.5D Hyperbolic Lattice (cyclic flow + semantic weighting)
# ===================================================================


class TestHyperbolicLattice25D:
    def test_phase_normalization(self):
        lat = HyperbolicLattice25D(cell_size=0.25)
        b = lat.insert_bundle(0.1, 0.1, phase_rad=8.5, tongue="KO")
        assert 0.0 <= b.phase_rad < (2.0 * math.pi)

    def test_overlap_cells_detected(self):
        lat = HyperbolicLattice25D(cell_size=0.5)
        lat.insert_bundle(0.10, 0.10, phase_rad=0.1, tongue="KO", intent_vector=[1, 0, 0])
        lat.insert_bundle(0.12, 0.11, phase_rad=0.2, tongue="DR", intent_vector=[1, 0, 0])
        overlaps = lat.overlapping_cells(min_bundles=2)
        assert len(overlaps) >= 1

    def test_cyclic_phase_distance_wraps(self):
        a = 0.05
        b = 2 * math.pi - 0.05
        d = HyperbolicLattice25D.cyclic_phase_distance(a, b)
        assert d < 0.05

    def test_query_nearest_prefers_semantic_alignment(self):
        lat = HyperbolicLattice25D(cell_size=0.5, phase_weight=0.2)
        near_sem = lat.insert_bundle(
            0.1, 0.1, phase_rad=0.1, tongue="DR", intent_vector=[1, 0, 0], intent_label="near_sem"
        )
        lat.insert_bundle(0.1, 0.1, phase_rad=0.1, tongue="KO", intent_vector=[0, 1, 0], intent_label="off_sem")

        res = lat.query_nearest(0.1, 0.1, phase_rad=0.1, intent_vector=[1, 0, 0], tongue="DR", top_k=1)
        assert len(res) == 1
        assert res[0][0].bundle_id == near_sem.bundle_id

    def test_lace_edges_exist_between_neighbor_cells(self):
        lat = HyperbolicLattice25D(cell_size=0.5)
        lat.insert_bundle(-0.75, -0.75, phase_rad=0.0, tongue="KO")
        lat.insert_bundle(-0.26, -0.76, phase_rad=0.1, tongue="AV")
        edges = lat.lace_edges()
        assert len(edges) >= 1

    def test_advance_cycle_rebuilds_octree_projection(self):
        lat = HyperbolicLattice25D(cell_size=0.5)
        lat.insert_bundle(0.2, 0.2, phase_rad=0.0, tongue="KO", intent_label="c0")
        before = lat.octree.stats()["count"]
        lat.advance_cycle(math.pi / 2)
        after = lat.octree.stats()["count"]
        assert before == after == 1

    def test_stats_include_overlap_and_semantic_weight(self):
        lat = HyperbolicLattice25D(cell_size=0.5)
        lat.insert_bundle(0.1, 0.1, phase_rad=0.0, tongue="KO")
        lat.insert_bundle(0.12, 0.12, phase_rad=0.3, tongue="DR")
        s = lat.stats()
        assert s["bundle_count"] == 2
        assert s["semantic_weight_sum"] > 0.0
        assert "overlap_cells" in s

    def test_quadtree_index_mode_exposes_stats(self):
        lat = HyperbolicLattice25D(
            cell_size=0.25,
            index_mode="quadtree",
            quadtree_capacity=2,
            quadtree_z_variance=0.0,
        )
        for i in range(8):
            lat.insert_bundle(
                x=math.cos(i * 0.4) * 0.7,
                y=math.sin(i * 0.5) * 0.7,
                phase_rad=i * 0.37,
                tongue="KO",
                intent_vector=[1.0, 0.0, 0.0],
            )
        s = lat.stats()
        assert s["index_mode"] == "quadtree"
        assert "quadtree" in s
        assert s["quadtree"]["entry_count"] == 8
        assert s["quadtree"]["node_count"] >= 1

    def test_hybrid_index_query_returns_results(self):
        lat = HyperbolicLattice25D(
            cell_size=0.4,
            index_mode="hybrid",
            quadtree_capacity=2,
            quadtree_z_variance=0.0,
            quadtree_query_extent=0.2,
        )
        for i in range(6):
            lat.insert_bundle(
                x=-0.6 + i * 0.2,
                y=-0.5 + i * 0.15,
                phase_rad=i * 0.4,
                tongue="DR" if i % 2 else "KO",
                intent_vector=[0.9, 0.1, 0.0],
                intent_label=f"b{i}",
            )
        out = lat.query_nearest(
            x=-0.2,
            y=-0.1,
            phase_rad=0.4,
            intent_vector=[0.9, 0.1, 0.0],
            top_k=3,
        )
        assert len(out) == 3
        assert all(isinstance(row[0].bundle_id, str) for row in out)


class TestAdaptiveQuadtree25D:
    def test_query_window_wraps_boundaries(self):
        qt = AdaptiveQuadtree25D(max_depth=4, capacity=1, z_variance_threshold=0.0)
        b1 = CyclicBundle25D(bundle_id="a", x=0.95, y=0.95, phase_rad=0.1)
        b2 = CyclicBundle25D(bundle_id="b", x=-0.96, y=-0.95, phase_rad=0.2)
        qt.insert_bundle(b1)
        qt.insert_bundle(b2)
        ids = qt.query_window(0.99, 0.99, half_extent=0.08)
        assert "a" in ids
        ids_wrap = qt.query_window(-0.99, -0.99, half_extent=0.08)
        assert "b" in ids_wrap

    def test_lod_mesh_contains_leaf_tiles(self):
        qt = AdaptiveQuadtree25D(max_depth=4, capacity=1, z_variance_threshold=0.0)
        qt.insert_bundle(CyclicBundle25D(bundle_id="a", x=0.1, y=0.1, phase_rad=0.5))
        qt.insert_bundle(CyclicBundle25D(bundle_id="b", x=0.2, y=0.2, phase_rad=1.5))
        mesh = qt.lod_mesh()
        assert len(mesh) >= 1
        assert "height" in mesh[0]
        assert "lod" in mesh[0]

    def test_quadtree_to_octree_projection(self):
        lat = HyperbolicLattice25D(cell_size=0.4, index_mode="quadtree", quadtree_capacity=1, quadtree_z_variance=0.0)
        lat.insert_bundle(0.1, 0.1, phase_rad=0.2, tongue="DR", intent_label="p0")
        lat.insert_bundle(-0.2, 0.3, phase_rad=1.0, tongue="KO", intent_label="p1")
        inserted = lat.project_quadtree_to_octree()
        assert inserted == 2
        assert lat.octree.stats()["count"] == 2
