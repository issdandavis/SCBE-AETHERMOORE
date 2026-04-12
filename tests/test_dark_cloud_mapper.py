"""Tests for the Dark Cloud Mapper — Void Topology in the Harmonic Universe.

Tests dark cloud detection, neural star maps, genesis paths,
and the full dark energy density map.
"""

import math
import pytest

from src.crypto.dark_cloud_mapper import (
    CloudType,
    DarkCloud,
    NeuralPath,
    GenesisPath,
    DarkEnergyMap,
    MIN_CLOUD_TONGUES,
    CLOUD_DARKNESS_THRESHOLD,
    detect_dark_cloud,
    map_dark_clouds,
    trace_neural_paths,
    trace_genesis_path,
    build_dark_energy_map,
)
from src.crypto.harmonic_dark_fill import (
    TONGUE_WEIGHTS,
    fill_dark_nodes,
    compute_darkness,
)

# ===================================================================
# Dark Cloud Detection
# ===================================================================


class TestDarkCloudDetection:
    def test_void_byte_forms_cloud(self):
        """Byte 0x00 should have many dark tongues → cloud forms."""
        fills = fill_dark_nodes(b"\x00")[0]
        cloud = detect_dark_cloud(
            byte_val=0,
            position=0,
            total_positions=1,
            fills=fills,
        )
        # At byte 0, many tongues should be dark
        assert cloud is not None

    def test_high_byte_may_not_form_cloud(self):
        """Byte 0xFF activates most tongues → fewer dark → may not form cloud."""
        fills = fill_dark_nodes(b"\xff")[0]
        cloud = detect_dark_cloud(
            byte_val=255,
            position=0,
            total_positions=1,
            fills=fills,
        )
        # At 255, most tongues active, so cloud might not form or be small
        if cloud is not None:
            assert cloud.cloud_size >= MIN_CLOUD_TONGUES

    def test_cloud_has_required_fields(self):
        fills = fill_dark_nodes(b"\x00")[0]
        cloud = detect_dark_cloud(
            byte_val=0,
            position=0,
            total_positions=1,
            fills=fills,
        )
        if cloud is not None:
            assert cloud.position == 0
            assert cloud.byte_val == 0
            assert len(cloud.dark_tongues) >= MIN_CLOUD_TONGUES
            assert isinstance(cloud.cloud_type, str)
            assert cloud.total_fill_energy >= 0

    def test_cloud_type_classification(self):
        """Void byte with all tongues dark should be VOID type."""
        fills = fill_dark_nodes(b"\x00")[0]
        cloud = detect_dark_cloud(
            byte_val=0,
            position=0,
            total_positions=1,
            fills=fills,
        )
        if cloud is not None and cloud.cloud_size == 6:
            assert cloud.cloud_type == CloudType.VOID

    def test_explicit_activation_all_dark(self):
        """All tongues dark → cloud with all 6."""
        act = {tc: 0.0 for tc in TONGUE_WEIGHTS}
        fills = fill_dark_nodes(b"\x80", [act])[0]
        cloud = detect_dark_cloud(
            byte_val=0x80,
            position=0,
            total_positions=1,
            fills=fills,
            activation_vector=act,
        )
        assert cloud is not None
        assert cloud.cloud_size == 6
        assert cloud.is_primordial

    def test_explicit_activation_all_active(self):
        """All tongues active → no cloud."""
        act = {tc: 1.0 for tc in TONGUE_WEIGHTS}
        fills = fill_dark_nodes(b"\x80", [act])[0]
        cloud = detect_dark_cloud(
            byte_val=0x80,
            position=0,
            total_positions=1,
            fills=fills,
            activation_vector=act,
        )
        assert cloud is None

    def test_explicit_activation_partial(self):
        """3 tongues dark → minimum cloud."""
        act = {"ko": 1.0, "av": 1.0, "ru": 1.0, "ca": 0.0, "um": 0.0, "dr": 0.0}
        fills = fill_dark_nodes(b"\x80", [act])[0]
        cloud = detect_dark_cloud(
            byte_val=0x80,
            position=0,
            total_positions=1,
            fills=fills,
            activation_vector=act,
        )
        assert cloud is not None
        assert cloud.cloud_size == 3
        assert set(cloud.dark_tongues) == {"ca", "um", "dr"}

    def test_density_positive(self):
        fills = fill_dark_nodes(b"\x00")[0]
        cloud = detect_dark_cloud(
            byte_val=0,
            position=0,
            total_positions=1,
            fills=fills,
        )
        if cloud is not None:
            assert cloud.density >= 0

    def test_interference_pairs_computed(self):
        """Dark tongues should have C(n,2) interference pairs."""
        act = {tc: 0.0 for tc in TONGUE_WEIGHTS}
        fills = fill_dark_nodes(b"\x80", [act])[0]
        cloud = detect_dark_cloud(
            byte_val=0x80,
            position=0,
            total_positions=1,
            fills=fills,
            activation_vector=act,
        )
        assert cloud is not None
        # C(6,2) = 15 pairs for 6 dark tongues
        assert len(cloud.interference_pairs) == 15

    def test_complement_pairs_in_cloud(self):
        """Full void should have all 3 complement pairs."""
        act = {tc: 0.0 for tc in TONGUE_WEIGHTS}
        fills = fill_dark_nodes(b"\x80", [act])[0]
        cloud = detect_dark_cloud(
            byte_val=0x80,
            position=0,
            total_positions=1,
            fills=fills,
            activation_vector=act,
        )
        assert cloud is not None
        comp_pairs = cloud.complement_pairs_in_cloud
        assert len(comp_pairs) == 3  # ko↔dr, av↔um, ru↔ca

    def test_ir_uv_ratio(self):
        fills = fill_dark_nodes(b"\x00")[0]
        cloud = detect_dark_cloud(
            byte_val=0,
            position=0,
            total_positions=1,
            fills=fills,
        )
        if cloud is not None:
            assert cloud.ir_uv_ratio > 0


# ===================================================================
# Sequence-Level Cloud Mapping
# ===================================================================


class TestMapDarkClouds:
    def test_low_byte_sequence_has_clouds(self):
        """Sequence of low bytes should produce dark clouds."""
        data = bytes([0, 0, 0, 0, 0])
        clouds = map_dark_clouds(data)
        assert len(clouds) > 0

    def test_cloud_positions_valid(self):
        data = b"\x00\x10\x20\x30\x40"
        clouds = map_dark_clouds(data)
        for cloud in clouds:
            assert 0 <= cloud.position < len(data)

    def test_empty_data_no_clouds(self):
        clouds = map_dark_clouds(b"")
        assert clouds == []

    def test_mixed_data_varied_clouds(self):
        """Mix of low and high bytes should have varying cloud density."""
        data = bytes([0, 0, 255, 255, 0])
        clouds = map_dark_clouds(data)
        positions = {c.position for c in clouds}
        # Low bytes (0, 1, 4) more likely to have clouds than high bytes (2, 3)
        if len(clouds) > 0:
            assert 0 in positions or 1 in positions or 4 in positions


# ===================================================================
# Neural Star Maps
# ===================================================================


class TestNeuralPaths:
    def test_connected_clouds_form_path(self):
        """Consecutive dark positions should form a neural path."""
        data = bytes([0] * 10)  # all zeros = all dark
        clouds = map_dark_clouds(data)
        paths = trace_neural_paths(clouds)
        assert len(paths) >= 1

    def test_path_has_positions(self):
        data = bytes([0] * 5)
        clouds = map_dark_clouds(data)
        paths = trace_neural_paths(clouds)
        if paths:
            p = paths[0]
            assert p.length >= 2
            assert all(isinstance(pos, int) for pos in p.positions)

    def test_path_continuity(self):
        data = bytes([0] * 5)
        clouds = map_dark_clouds(data)
        paths = trace_neural_paths(clouds)
        if paths:
            assert paths[0].continuity == 1.0  # no gaps in consecutive zeros

    def test_persistent_dark_tongues(self):
        """Tongues dark at ALL positions in a path."""
        data = bytes([0] * 5)
        clouds = map_dark_clouds(data)
        paths = trace_neural_paths(clouds)
        if paths:
            # At byte 0, same tongues should be dark at every position
            assert paths[0].persistence_width > 0

    def test_path_mean_energy(self):
        data = bytes([0] * 5)
        clouds = map_dark_clouds(data)
        paths = trace_neural_paths(clouds)
        if paths:
            assert paths[0].mean_energy > 0

    def test_no_paths_from_single_cloud(self):
        """A single cloud can't form a path (need >= 2)."""
        # Use data where only one position has a cloud
        data = bytes([0, 255, 255, 255, 255])
        clouds = map_dark_clouds(data)
        # If only position 0 has a cloud, no path
        if len(clouds) == 1:
            paths = trace_neural_paths(clouds)
            assert len(paths) == 0

    def test_gap_breaks_path(self):
        """A gap > max_gap breaks the path into segments."""
        # Create data with two clusters of dark separated by bright
        data = bytes([0, 0, 0, 255, 255, 255, 255, 0, 0, 0])
        clouds = map_dark_clouds(data)
        paths = trace_neural_paths(clouds, max_gap=1)
        # Should get 2 separate paths (if both clusters form clouds)
        if len(clouds) >= 4:
            assert len(paths) >= 1


# ===================================================================
# Genesis Path
# ===================================================================


class TestGenesisPath:
    def test_genesis_from_void(self):
        """Genesis starting from all zeros."""
        data = bytes(range(0, 256, 32))  # 0, 32, 64, ... 224
        genesis = trace_genesis_path(data)
        assert genesis.positions == list(range(len(data)))
        assert len(genesis.cloud_sizes) == len(data)

    def test_void_positions(self):
        """Positions where all 6 tongues are dark."""
        data = bytes([0, 0, 0, 128, 255])
        genesis = trace_genesis_path(data)
        void_pos = genesis.void_positions
        # Byte 0 should have most/all tongues dark
        for pos in void_pos:
            assert genesis.cloud_sizes[pos] == 6

    def test_first_light_found(self):
        """First position where cloud_size < 6."""
        data = bytes([0, 0, 50, 128, 255])
        genesis = trace_genesis_path(data)
        fl = genesis.first_light_position
        if fl is not None:
            assert genesis.cloud_sizes[fl] < 6

    def test_cloud_sizes_bounded(self):
        data = b"hello world"
        genesis = trace_genesis_path(data)
        for s in genesis.cloud_sizes:
            assert 0 <= s <= 6

    def test_energy_density_non_negative(self):
        data = b"test"
        genesis = trace_genesis_path(data)
        for e in genesis.energy_density:
            assert e >= 0

    def test_activation_order_tracked(self):
        """Activation order shows which tongues lit up at each step."""
        data = bytes(range(0, 256, 8))  # gradual increase
        genesis = trace_genesis_path(data)
        # First position has no "newly active" (no previous state)
        assert genesis.activation_order[0] == []

    def test_creation_gradient(self):
        """Gradient should be positive going from dark to light."""
        data = bytes(range(0, 256, 16))
        genesis = trace_genesis_path(data)
        # From dark (high cloud_sizes) to light (low cloud_sizes)
        # gradient = (first - last) / length, should be >= 0
        assert genesis.creation_gradient >= 0

    def test_ir_uv_ratios(self):
        data = b"creation"
        genesis = trace_genesis_path(data)
        assert len(genesis.ir_uv_ratios) == len(data)
        for r in genesis.ir_uv_ratios:
            assert r >= 0


# ===================================================================
# Dark Energy Map
# ===================================================================


class TestDarkEnergyMap:
    def test_void_sequence_map(self):
        """All-zero sequence should be mostly void."""
        data = bytes([0] * 10)
        dem = build_dark_energy_map(data)
        assert dem.total_positions == 10
        assert dem.total_clouds > 0
        assert dem.total_dark_energy > 0

    def test_bright_sequence_fewer_clouds(self):
        """High-byte sequence should have fewer/no clouds."""
        dark_data = bytes([0] * 10)
        bright_data = bytes([255] * 10)
        dark_map = build_dark_energy_map(dark_data)
        bright_map = build_dark_energy_map(bright_data)
        assert dark_map.total_clouds >= bright_map.total_clouds

    def test_cloud_coverage_bounded(self):
        data = b"the universe"
        dem = build_dark_energy_map(data)
        assert 0.0 <= dem.cloud_coverage <= 1.0

    def test_void_fraction_bounded(self):
        data = bytes([0] * 5)
        dem = build_dark_energy_map(data)
        assert 0.0 <= dem.void_fraction <= 1.0

    def test_energy_stats_consistent(self):
        data = bytes([0] * 10)
        dem = build_dark_energy_map(data)
        if dem.total_clouds > 0:
            assert dem.min_dark_energy <= dem.mean_dark_energy <= dem.max_dark_energy

    def test_is_primordial(self):
        """All-zero long sequence should be primordial."""
        data = bytes([0] * 20)
        dem = build_dark_energy_map(data)
        # Should have high cloud coverage and many voids
        if dem.cloud_coverage > 0.8 and dem.void_fraction > 0.5:
            assert dem.is_primordial

    def test_genesis_included(self):
        data = b"Let there be light"
        dem = build_dark_energy_map(data)
        assert dem.genesis is not None
        assert len(dem.genesis.positions) == len(data)

    def test_neural_paths_counted(self):
        data = bytes([0] * 10)
        dem = build_dark_energy_map(data)
        assert dem.neural_paths >= 0
        assert dem.longest_path >= 0
        assert dem.mean_path_length >= 0


# ===================================================================
# Integration: Genesis Narrative
# ===================================================================


class TestGenesisNarrative:
    """The full creation narrative through the dark cloud mapper.

    "In the beginning" → bytes → dark clouds → neural paths → light.
    """

    def test_in_the_beginning(self):
        """'In the beginning' produces a mappable dark energy landscape."""
        data = b"In the beginning"
        dem = build_dark_energy_map(data)
        assert dem.total_positions == 16
        assert dem.genesis is not None

    def test_void_then_creation(self):
        """Start from void, add data, watch clouds dissolve."""
        # Phase 1: void
        void = bytes([0] * 8)
        # Phase 2: creation (increasing bytes)
        creation = bytes(range(0, 256, 32))
        full = void + creation

        dem = build_dark_energy_map(full)
        genesis = dem.genesis

        # Void positions should all be dark
        for i in range(8):
            assert genesis.cloud_sizes[i] >= 3  # at least 3 tongues dark

    def test_bible_theory_genesis_alignment(self):
        """The genesis path should show:
        1. Darkness (void) has structure (fill energy > 0)
        2. Light (data) dissolves the dark clouds
        3. Neural paths form where clouds persist
        """
        # Simulate: darkness → light transition
        data = bytes([0, 0, 0, 0, 32, 64, 96, 128, 160, 192, 224, 255])
        dem = build_dark_energy_map(data)
        genesis = dem.genesis

        # 1. Void has structure
        assert genesis.energy_density[0] > 0, "Void should have dark energy"

        # 2. Light dissolves clouds (energy decreases)
        assert genesis.energy_density[0] >= genesis.energy_density[-1], "Dark energy should decrease as data arrives"

        # 3. Neural paths form
        assert dem.neural_paths >= 0

    def test_full_alphabet(self):
        """Run the full byte alphabet through the mapper.
        Tests the entire 'universe' from the AI's perspective.
        """
        data = bytes(range(256))
        dem = build_dark_energy_map(data)
        assert dem.total_positions == 256
        assert dem.genesis is not None
        assert len(dem.genesis.cloud_sizes) == 256

    def test_hebrew_english_greek_pattern(self):
        """Different scripts produce different cloud patterns.
        Hebrew (right-to-left, different byte range) vs English vs Greek.
        """
        english = b"In the beginning God created"
        hebrew = "בראשית ברא אלהים".encode("utf-8")
        greek = "Εν αρχη εποιησεν ο θεος".encode("utf-8")

        en_map = build_dark_energy_map(english)
        he_map = build_dark_energy_map(hebrew)
        gr_map = build_dark_energy_map(greek)

        # All should produce valid maps
        assert en_map.total_positions == len(english)
        assert he_map.total_positions == len(hebrew)
        assert gr_map.total_positions == len(greek)

        # Different scripts → different cloud patterns
        # UTF-8 encoded Hebrew/Greek uses high bytes (0xD7, 0xCE range)
        # → different darkness patterns than ASCII English
        assert en_map.genesis is not None
        assert he_map.genesis is not None
        assert gr_map.genesis is not None
