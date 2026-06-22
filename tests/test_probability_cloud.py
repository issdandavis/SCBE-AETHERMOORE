"""Tests for probability_cloud -- the multi-point belief-cloud-over-gate-topography engine.

Locks the load-bearing behaviors: the cloud routes AROUND a locked gate (multi-option resilience), pools
into the deepest accessible well, reports 'stuck' when the whole field is peaks, widens reach with sigma,
and composes with a skillcheck menu (the cloud is the skill-check's continuous substrate).
"""

from __future__ import annotations

from python.scbe.probability_cloud import Site, convolve, diffuse, from_skill_menu, resolve, topography
from python.scbe.skillcheck import Option


def test_cloud_routes_around_a_locked_gate():
    # belief sits exactly on the most appealing option, but it's locked -> flow goes to the next well
    sites = [Site("login", 0.0, 0.95, locked=True), Site("search", 1.0, 0.7), Site("help", 2.0, 0.4)]
    r = resolve(sites, belief=0.0, sigma=0.7)
    assert r["choice"] == "search" and not r["stuck"]
    assert r["density"]["login"] == 0.0  # the locked peak is clipped to zero mass


def test_pools_into_deepest_accessible_well():
    r = resolve([Site("a", 0.0, 0.7), Site("b", 1.0, 0.4)], belief=0.5, sigma=1.0)
    assert r["choice"] == "a"  # equal reach, deeper well wins


def test_all_peaks_is_stuck():
    r = resolve([Site("x", 0.0, 0.9, locked=True), Site("y", 1.0, 0.8, locked=True)], belief=0.0)
    assert r["choice"] is None and r["stuck"] is True  # no accessible mass -> escalate


def test_uncertainty_widens_reach():
    sites = [Site("near", 0.0, 0.5), Site("far", 5.0, 0.9)]
    tight = resolve(sites, belief=0.0, sigma=0.5)  # can't reach the far (better) well
    wide = resolve(sites, belief=0.0, sigma=5.0)  # enough uncertainty to reach it
    assert tight["choice"] == "near"
    assert wide["density"]["far"] > tight["density"]["far"]  # more reach with more sigma


def test_convolution_clips_at_peaks_and_pools_at_wells():
    sites = [Site("w", 0.0, 0.9), Site("p", 0.0, 0.9, locked=True)]
    cloud = diffuse(sites, belief=0.0, sigma=1.0)
    dens = convolve(cloud, topography(sites))
    assert dens["w"] > 0 and dens["p"] == 0.0  # same position, same cloud mass: well keeps it, peak clips it


def test_composes_with_skill_menu():
    # the cloud runs over the SAME options a skillcheck menu produces (confidence->well, locked->peak)
    opts = [
        Option(0, "click", "r0", None, "[Click] 'ok'", "open", "", 0.9),
        Option(1, "click", "r1", None, "[Click] 'bad'", "locked", "", 0.2),
    ]
    sites = from_skill_menu(opts)
    r = resolve(sites, belief=0.0, sigma=1.0)
    assert r["choice"] == "click:r0"  # flows to the open high-confidence option, not the locked one
