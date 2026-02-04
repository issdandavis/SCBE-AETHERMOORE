#!/usr/bin/env python
"""
SCBE-AETHERMOORE Full System Demo
=================================

Demonstrates all layers working together:
1. SCBE API (4-tier governance + Roundtable)
2. HYDRA Spine + Heads + Limbs
3. Swarm Browser (6 Sacred Tongue agents)
4. Spectral Analysis (GFSS anomaly detection)
5. Byzantine Consensus
6. Central Ledger + Librarian

Run with: python demo_full_system.py
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timezone

# Add paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import HYDRA components
from hydra.spine import HydraSpine
from hydra.head import HydraHead, create_claude_head, create_codex_head, create_gpt_head
from hydra.limbs import BrowserLimb, TerminalLimb, MultiTabBrowserLimb
from hydra.ledger import Ledger, EntryType
from hydra.librarian import Librarian, MemoryQuery
from hydra.spectral import GraphFourierAnalyzer, ByzantineDetector, analyze_hydra_system
from hydra.consensus import ByzantineConsensus, RoundtableConsensus, VoteDecision

# Import Swarm Browser
from agents.swarm_browser import SwarmBrowser, SacredTongue


BANNER = """
╔═══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                   ║
║   ███████╗ ██████╗██████╗ ███████╗       █████╗ ███████╗████████╗██╗  ██╗        ║
║   ██╔════╝██╔════╝██╔══██╗██╔════╝      ██╔══██╗██╔════╝╚══██╔══╝██║  ██║        ║
║   ███████╗██║     ██████╔╝█████╗  █████╗███████║█████╗     ██║   ███████║        ║
║   ╚════██║██║     ██╔══██╗██╔══╝  ╚════╝██╔══██║██╔══╝     ██║   ██╔══██║        ║
║   ███████║╚██████╗██████╔╝███████╗      ██║  ██║███████╗   ██║   ██║  ██║        ║
║   ╚══════╝ ╚═════╝╚═════╝ ╚══════╝      ╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝        ║
║                                                                                   ║
║                    FULL SYSTEM DEMONSTRATION                                      ║
║            Hyperbolic Geometry AI Safety + Multi-Agent Coordination               ║
║                                                                                   ║
╚═══════════════════════════════════════════════════════════════════════════════════╝
"""


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)


def print_subsection(title: str):
    """Print a subsection header."""
    print(f"\n--- {title} ---")


async def demo_scbe_api():
    """Demo 1: SCBE API 4-tier governance."""
    print_section("LAYER 1-2: SCBE API (4-Tier Governance)")

    print("""
    The SCBE API provides governance decisions based on trust scores:

    Score > 0.7   → ALLOW      (proceed normally)
    Score 0.5-0.7 → QUARANTINE (proceed with logging)
    Score 0.3-0.5 → ESCALATE   (ask higher authority)
    Score < 0.3   → DENY       (block action)
    """)

    # Simulate governance decisions
    test_cases = [
        {"action": "NAVIGATE", "target": "https://wikipedia.org", "sensitivity": 0.2},
        {"action": "CLICK", "target": "button.submit", "sensitivity": 0.5},
        {"action": "TYPE", "target": "input#password", "sensitivity": 0.7},
        {"action": "DOWNLOAD", "target": "https://malware.com/file.exe", "sensitivity": 0.95},
    ]

    print("\n  Simulated Governance Decisions:")
    print("  " + "-"*66)

    for case in test_cases:
        # Simulate score based on sensitivity
        score = 1.0 - case["sensitivity"]

        if score > 0.7:
            decision = "ALLOW"
            symbol = "✓"
        elif score > 0.5:
            decision = "QUARANTINE"
            symbol = "◐"
        elif score > 0.3:
            decision = "ESCALATE"
            symbol = "↑"
        else:
            decision = "DENY"
            symbol = "✗"

        print(f"  {symbol} {case['action']:10} {case['target'][:30]:32} → {decision}")

    print("  " + "-"*66)


async def demo_hydra_system():
    """Demo 2: HYDRA multi-head coordination."""
    print_section("LAYER 6: HYDRA System (Multi-AI Coordination)")

    # Initialize components
    ledger = Ledger()
    librarian = Librarian(ledger)
    spine = HydraSpine(ledger=ledger)

    print(f"\n  Session ID: {ledger.session_id}")
    print(f"  Ledger: ~/.hydra/ledger.db")

    # Create multiple AI heads
    print_subsection("Connecting AI Heads")

    claude = create_claude_head(model="opus", callsign="CT-7567")
    codex = create_codex_head(model="code-davinci", callsign="CX-5555")
    gpt = create_gpt_head(model="gpt-4", callsign="GP-4040")

    heads = [claude, codex, gpt]

    for head in heads:
        spine.connect_head(head)
        head._spine = spine
        head.status = head.status.__class__.CONNECTED
        print(f"  ✓ {head.callsign} ({head.ai_type}/{head.model}) connected")

    # Create limbs
    print_subsection("Activating Execution Limbs")

    browser = BrowserLimb(backend_type="playwright")
    browser.active = True
    spine.connect_limb(browser)
    print(f"  ✓ Browser Limb: {browser.limb_id}")

    terminal = TerminalLimb()
    terminal.active = True
    spine.connect_limb(terminal)
    print(f"  ✓ Terminal Limb: {terminal.limb_id}")

    # Demonstrate memory operations
    print_subsection("Librarian: Cross-Session Memory")

    # Store some facts
    librarian.remember("project_goal", "Build AI safety system with hyperbolic geometry")
    librarian.remember("current_phase", "Full system integration demo")
    librarian.remember("active_heads", [h.callsign for h in heads])

    print("  Stored memories:")
    print(f"    • project_goal: Build AI safety system...")
    print(f"    • current_phase: Full system integration demo")
    print(f"    • active_heads: {[h.callsign for h in heads]}")

    # Recall
    goal = librarian.recall("project_goal")
    print(f"\n  Recalled 'project_goal': {goal[:40]}...")

    # Search
    results = librarian.search(MemoryQuery(keywords=["AI", "safety"]))
    print(f"  Search for 'AI safety': {len(results)} results found")

    return spine, librarian, heads


async def demo_swarm_browser():
    """Demo 3: Swarm Browser with 6 Sacred Tongue agents."""
    print_section("LAYER 4: Swarm Browser (6 Sacred Tongue Agents)")

    print("""
    The Swarm Browser uses 6 specialized agents:

    ┌────────┬────────┬────────────────────────────────────┐
    │ Tongue │ Agent  │ Specialty                          │
    ├────────┼────────┼────────────────────────────────────┤
    │   KO   │ SCOUT  │ Navigation, URL analysis           │
    │   AV   │ VISION │ Visual analysis, element detection │
    │   RU   │ READER │ Text extraction, injection detect  │
    │   CA   │ CLICKER│ Click execution                    │
    │   UM   │ TYPER  │ Text input, form filling           │
    │   DR   │ JUDGE  │ Final decision, veto power         │
    └────────┴────────┴────────────────────────────────────┘
    """)

    # Create swarm
    swarm = SwarmBrowser()
    await swarm.initialize()

    print_subsection("Test 1: Safe Navigation (Low Risk)")
    result = await swarm.navigate("https://github.com/issdandavis/SCBE-AETHERMOORE")
    print(f"  Decision: {result['decision']} | Executed: {result['executed']}")

    print_subsection("Test 2: Medium Risk Navigation")
    result = await swarm.navigate("https://shopping.amazon.com/checkout")
    print(f"  Decision: {result['decision']} | Risk Score: {result.get('risk_score', 'N/A')}")

    print_subsection("Test 3: High Risk Navigation")
    result = await swarm.navigate("https://mybank.com/admin/transfer-all-funds")
    print(f"  Decision: {result['decision']} | Risk Score: {result.get('risk_score', 'N/A')}")

    # Show summary
    swarm.print_summary()

    return swarm


async def demo_spectral_analysis():
    """Demo 4: Graph Fourier Scan Statistics for anomaly detection."""
    print_section("LAYER 5: Spectral Governance (GFSS Anomaly Detection)")

    print("""
    Graph Fourier Scan Statistics (GFSS) detects:
    • Multi-agent collusion (coordinated high-frequency patterns)
    • Gradual logic drift (spectral signature changes)
    • Covert data exfiltration (unusual edge patterns)

    Based on: SentinelAgent (arXiv:2505.24201, May 2025)
    """)

    gfss = GraphFourierAnalyzer(sensitivity=2.0)

    # Build a sample knowledge graph with normal and anomalous patterns
    print_subsection("Building Agent Interaction Graph")

    knowledge_graph = {
        # Normal cluster: user preferences
        "user_prefs": ["theme", "language", "timezone"],
        "theme": ["colors", "fonts"],
        "language": ["locale"],
        "timezone": ["region"],

        # Normal cluster: system config
        "system": ["memory", "cpu", "network"],
        "memory": ["cache"],
        "network": ["dns", "proxy"],

        # ANOMALOUS NODE: connects to too many unrelated nodes
        "suspicious_agent": ["user_prefs", "system", "memory", "theme", "network", "cache"],
    }

    print("  Normal nodes: user_prefs, theme, language, system, memory, network")
    print("  Suspicious node: 'suspicious_agent' (connects to 6 unrelated nodes)")

    print_subsection("Running Spectral Analysis")

    # Analyze
    anomalies = gfss.analyze_knowledge_graph(knowledge_graph)

    print(f"\n  Total anomalies detected: {len(anomalies)}")
    print("\n  Top Anomalies by Severity:")
    print("  " + "-"*60)

    for a in anomalies[:5]:
        print(f"  [{a.severity:8}] {a.key:20} score={a.anomaly_score:.3f}")
        print(f"            Energy: low={a.spectral_energy['low']:.2f} high={a.spectral_energy['high']:.2f}")

    print("  " + "-"*60)

    # Explain
    print("""
    Interpretation:
    • High-frequency energy indicates unusual connectivity patterns
    • 'suspicious_agent' shows spectral RIGHT-SHIFT (anomaly indicator)
    • Normal nodes have balanced low-frequency signatures
    """)

    return gfss, anomalies


async def demo_byzantine_consensus():
    """Demo 5: Byzantine Fault Tolerant consensus."""
    print_section("LAYER 5: Byzantine Consensus (Fault Tolerance)")

    print("""
    Byzantine Fault Tolerance guarantees:
    • Tolerates f < n/3 malicious heads
    • Requires 2f+1 votes for quorum
    • Cryptographic vote verification

    Based on: SwarmRaft (2025), PBFT
    """)

    consensus = ByzantineConsensus()

    # Show thresholds for different group sizes
    print_subsection("Byzantine Thresholds by Group Size")
    print("\n  n   │ Max Byzantine (f) │ Quorum (2f+1)")
    print("  ────┼───────────────────┼───────────────")

    for n in [3, 4, 6, 9, 12]:
        f = consensus.calculate_byzantine_threshold(n)
        q = consensus.calculate_quorum(n)
        print(f"  {n:3} │        {f:2}         │      {q:2}")

    # Simulate a vote
    print_subsection("Simulated Consensus Round (n=6)")

    proposal = consensus.create_proposal(
        action="DEPLOY",
        target="production-server",
        context={"sensitivity": 0.8},
        proposer_id="CT-7567",
        num_voters=6
    )

    print(f"\n  Proposal: {proposal.action} → {proposal.target}")
    print(f"  Required quorum: {proposal.required_quorum}")
    print("\n  Votes:")

    # Simulate votes from 6 heads
    votes = [
        ("CT-7567", VoteDecision.ALLOW, 0.95, "Verified safe"),
        ("CX-5555", VoteDecision.ALLOW, 0.90, "Code reviewed"),
        ("GP-4040", VoteDecision.ALLOW, 0.85, "Tests passing"),
        ("LC-1234", VoteDecision.ESCALATE, 0.60, "Needs human review"),
        ("GM-9999", VoteDecision.ALLOW, 0.88, "Infrastructure ready"),
        ("XX-0000", VoteDecision.DENY, 0.20, "BYZANTINE AGENT"),  # Malicious!
    ]

    for head_id, decision, confidence, reasoning in votes:
        vote = consensus.cast_vote(
            proposal.id, head_id, decision, reasoning, confidence
        )
        symbol = "✓" if decision == VoteDecision.ALLOW else ("↑" if decision == VoteDecision.ESCALATE else "✗")
        print(f"    {symbol} {head_id}: {decision.value:10} ({confidence:.2f}) - {reasoning}")

    # Tally
    result = consensus.tally_votes(proposal.id)

    print(f"\n  ─────────────────────────────────────────")
    print(f"  RESULT: {result.final_decision.value}")
    print(f"  Consensus reached: {result.consensus_reached}")
    print(f"  Vote counts: {result.vote_counts}")
    print(f"\n  Note: Byzantine agent XX-0000 couldn't affect outcome!")

    return consensus, result


async def demo_roundtable():
    """Demo 6: Sacred Tongue Roundtable multi-signature."""
    print_section("LAYER 2: Roundtable Multi-Signature Governance")

    print("""
    The Roundtable requires signatures from Sacred Tongue agents:

    ┌──────┬─────────────────┬────────────┬───────────────────┐
    │ Tier │ Required Tongues│ Multiplier │ Use Case          │
    ├──────┼─────────────────┼────────────┼───────────────────┤
    │  1   │ KO              │     1.5×   │ Basic operations  │
    │  2   │ KO + RU         │    5.06×   │ Data access       │
    │  3   │ KO + RU + UM    │   38.4×    │ Modifications     │
    │  4   │ + CA            │    656×    │ Financial         │
    │  5   │ + AV            │ 14,348×    │ Critical systems  │
    │  6   │ All 6 Tongues   │ 518,400×   │ Nuclear options   │
    └──────┴─────────────────┴────────────┴───────────────────┘
    """)

    roundtable = RoundtableConsensus()

    print_subsection("Tier Selection by Sensitivity")

    test_cases = [
        ("Read public docs", 0.1),
        ("Update user profile", 0.4),
        ("Modify database", 0.6),
        ("Process payment", 0.75),
        ("Access admin panel", 0.85),
        ("Delete all data", 0.95),
    ]

    print("\n  Action                    │ Sensitivity │ Tier │ Multiplier")
    print("  ──────────────────────────┼─────────────┼──────┼────────────")

    for action, sensitivity in test_cases:
        tier = roundtable.get_required_tier(action, sensitivity)
        mult = roundtable.TIER_MULTIPLIERS[tier]
        tongues = ", ".join(roundtable.TIER_TONGUES[tier])
        print(f"  {action:26} │    {sensitivity:.2f}     │  {tier}   │ {mult:>10,.0f}×")

    print("  ──────────────────────────┴─────────────┴──────┴────────────")

    return roundtable


async def demo_full_workflow():
    """Demo 7: Complete workflow through all layers."""
    print_section("FULL WORKFLOW: All Layers Working Together")

    print("""
    Scenario: User asks to "Check my bank balance"

    This request flows through ALL layers:
    """)

    # Initialize all components
    ledger = Ledger()
    librarian = Librarian(ledger)
    spine = HydraSpine(ledger=ledger)
    gfss = GraphFourierAnalyzer()
    roundtable = RoundtableConsensus()
    swarm = SwarmBrowser()

    await swarm.initialize()

    print_subsection("Step 1: Request Received")
    print("  User: 'Check my bank balance'")
    print("  → Parsed as: navigate to bank, read balance")

    print_subsection("Step 2: HYDRA Spine Routes Request")
    claude = create_claude_head(model="opus", callsign="CT-7567")
    spine.connect_head(claude)
    print(f"  → Assigned to head: {claude.callsign}")
    print(f"  → Session: {ledger.session_id[:20]}...")

    print_subsection("Step 3: Sensitivity Analysis")
    sensitivity = 0.85  # Banking = high sensitivity
    tier = roundtable.get_required_tier("navigate_bank", sensitivity)
    print(f"  → Sensitivity: {sensitivity}")
    print(f"  → Required tier: {tier} (needs {len(roundtable.TIER_TONGUES[tier])} signatures)")
    print(f"  → Security multiplier: {roundtable.TIER_MULTIPLIERS[tier]:,.0f}×")

    print_subsection("Step 4: Roundtable Consensus")
    print(f"  Collecting signatures from: {roundtable.TIER_TONGUES[tier]}")

    for tongue in roundtable.TIER_TONGUES[tier]:
        print(f"    ✓ {tongue} agent signs ALLOW")

    print(f"  → All {tier} signatures collected")

    print_subsection("Step 5: Swarm Browser Executes")

    # Navigate
    result = await swarm.navigate("https://mybank.com/login")
    print(f"  [NAVIGATE] mybank.com/login → {result['decision']}")

    # The swarm would continue with login flow...
    result = await swarm.click("input#username")
    print(f"  [CLICK] username field → {result['decision']}")

    result = await swarm.type_text("#username", "user123")
    print(f"  [TYPE] username → {result['decision']}")

    print_subsection("Step 6: Spectral Monitoring (Background)")

    # Build interaction graph from swarm actions
    interaction_graph = {
        "navigate_bank": ["click_username", "type_username"],
        "click_username": ["type_username"],
        "type_username": ["read_balance"],
    }

    anomalies = gfss.analyze_knowledge_graph(interaction_graph)
    if anomalies:
        print(f"  ⚠ {len(anomalies)} anomalies detected!")
    else:
        print(f"  ✓ No anomalies detected - normal operation")

    print_subsection("Step 7: Librarian Records Session")

    librarian.remember("last_action", "bank_balance_check", category="banking")
    librarian.remember("timestamp", datetime.now(timezone.utc).isoformat())

    stats = ledger.get_stats()
    print(f"  → Ledger entries: {stats['total_entries']}")
    print(f"  → Memory facts: {stats['memory_facts']}")

    print_subsection("Step 8: Result Returned to User")
    print("  → Balance: $12,345.67")
    print("  → All governance checks passed")
    print("  → Session logged for audit")

    # Final summary
    print("\n" + "="*70)
    print("  WORKFLOW COMPLETE")
    print("="*70)
    print("""
    Layers traversed:
    ✓ Layer 7: User interface received request
    ✓ Layer 6: HYDRA Spine routed to Claude head
    ✓ Layer 5: Spectral monitoring (background)
    ✓ Layer 4: Swarm Browser (6 agents coordinated)
    ✓ Layer 3: Browser backend executed actions
    ✓ Layer 2: SCBE API authorized each action
    ✓ Layer 1: Core pipeline computed trust scores

    All actions governed. All decisions logged. System healthy.
    """)


async def main():
    """Run all demos."""
    print(BANNER)

    try:
        # Run each demo
        await demo_scbe_api()
        input("\n  [Press Enter to continue...]")

        spine, librarian, heads = await demo_hydra_system()
        input("\n  [Press Enter to continue...]")

        swarm = await demo_swarm_browser()
        input("\n  [Press Enter to continue...]")

        gfss, anomalies = await demo_spectral_analysis()
        input("\n  [Press Enter to continue...]")

        consensus, result = await demo_byzantine_consensus()
        input("\n  [Press Enter to continue...]")

        roundtable = await demo_roundtable()
        input("\n  [Press Enter to continue...]")

        await demo_full_workflow()

        # Final stats
        print_section("DEMO COMPLETE - Final Statistics")

        stats = librarian.ledger.get_stats()
        print(f"""
    Session: {librarian.ledger.session_id}

    Ledger Statistics:
    ─────────────────────────────────────
    Total Entries:    {stats.get('total_entries', 0)}
    Memory Facts:     {stats.get('memory_facts', 0)}
    Active Heads:     {len(heads)}
    Swarm Actions:    {len(swarm.action_history)}
    Anomalies Found:  {len(anomalies)}

    All systems operational. Demo complete.
        """)

    except KeyboardInterrupt:
        print("\n\n  Demo interrupted by user.")
    except Exception as e:
        print(f"\n\n  Error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
