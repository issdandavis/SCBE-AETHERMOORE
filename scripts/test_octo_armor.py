"""Test the OctoArmor HYDRA multi-tentacle connector hub."""
import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Load .env
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                if val and key.strip():
                    os.environ.setdefault(key.strip(), val.strip())

from src.fleet.octo_armor import (
    OctoArmor, Tentacle, TrainingFlywheel,
    TENTACLE_REGISTRY, tentacle_dashboard,
    list_free_models,
)


def test_tentacle_status():
    print("=" * 70)
    print("  HYDRA OctoArmor — Tentacle Status Dashboard")
    print("  Polly flies above. The octopus reaches everywhere.")
    print("=" * 70)

    dashboard = tentacle_dashboard()
    ready = 0
    total = len(dashboard)

    for t in dashboard:
        icon = "+" if t["available"] else "-"
        print(f"  [{icon}] {t['tentacle']:15} {t['cost']:8} "
              f"RPM:{t['rpm']:10} RPD:{t['rpd']:12} "
              f"Models:{t['free_models']}")
        if t["available"]:
            ready += 1

    print()
    print(f"  READY: {ready}/{total} tentacles")
    print()


def test_free_models():
    print("=== ALL FREE MODELS ===")
    models = list_free_models()
    total = 0
    for provider, model_list in models.items():
        print(f"  {provider}:")
        for m in model_list:
            print(f"    - {m}")
            total += 1
    print(f"\n  Total free models: {total}")
    print()


def test_tokenizer_gateway():
    print("=== SCBE TOKENIZER GATEWAY ===")
    from src.fleet.octo_armor import TokenizerGateway
    gw = TokenizerGateway()

    for prompt, task_type in [
        ("Write unit tests for the auth module", "code"),
        ("Research competitor products in AI safety", "research"),
        ("Tell me a story about hyperbolic geometry", "creative"),
        ("Evaluate the governance pipeline security", "governance"),
    ]:
        enc = gw.encode_request(prompt, task_type)
        print(f"  [{enc['tongue']}] {task_type:12} fp:{enc['fingerprint'][:12]}... "
              f"| {prompt[:50]}")
    print()


def test_polly_observer():
    print("=== POLLY — The Raven Observer ===")
    from src.fleet.octo_armor import PollyLog

    polly = PollyLog()

    # Simulate observations
    for prompt, response, tentacle, model in [
        ("Explain quicksort", "Quicksort is a divide-and-conquer algorithm...",
         "groq", "llama-3.3-70b"),
        ("Write a haiku about AI", "Silicon dreams flow\nThrough hyperbolic gardens\nPolly watches all",
         "cerebras", "llama-3.3-70b"),
        ("Check security of auth module", "The auth module has 3 potential issues:\n1. No rate limiting\n2. Weak hashing\n3. Missing CSRF",
         "openrouter", "hermes-405b"),
    ]:
        obs = polly.observe(tentacle, model, "KO", prompt, response, 150.0)
        print(f"  [{obs.obs_id}] q:{obs.quality_score:.2f} "
              f"tags:{obs.topic_tags} | {prompt[:40]}")

    print()
    print("  Mind Map:", polly.get_mind_map())
    print()
    stats = polly.stats()
    print(f"  Stats: {stats['total']} observations, "
          f"{stats['training_pairs']} training pairs, "
          f"{stats['mind_map_topics']} topics")
    print()


async def test_live_reach():
    """Test live tentacle reach — only runs if keys available."""
    armor = OctoArmor()
    available = armor.available_tentacles()

    if not available:
        print("=== LIVE REACH: No tentacles available (set API keys in .env) ===")
        return

    print(f"=== LIVE REACH — Using {available[0].value} ===")

    result = await armor.reach(
        "You are a tentacle of the HYDRA OctoArmor system in SCBE-AETHERMOORE. "
        "Say: TENTACLE ONLINE. Then in one sentence, describe what a "
        "multi-provider AI governance connector does.",
    )

    if result["status"] == "ok":
        print(f"  Status:   {result['status']}")
        print(f"  Tentacle: {result['tentacle']}")
        print(f"  Model:    {result['model']}")
        print(f"  Tongue:   {result['tongue']}")
        print(f"  Latency:  {result['latency_ms']:.0f}ms")
        print(f"  Quality:  {result['quality']:.2f}")
        print(f"  Training: {result['training_pair_generated']}")
        print(f"  Response: {result['response'][:300]}")
    else:
        print(f"  Error: {result.get('error', 'unknown')}")

    print()
    print("=== POLLY STATS ===")
    stats = armor.polly.stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print()

    print("=== DIAGNOSTICS ===")
    diag = armor.diagnostics()
    print(f"  HYDRA Status: {diag['hydra_status']}")
    print(f"  Available: {diag['available_tentacles']}/{diag['total_tentacles']} tentacles")
    print(f"  Interactions: {diag['interactions']}")
    print(f"  Total free models: {diag['total_free_models']}")
    print()


def test_training_flywheel():
    print("=== TRAINING FLYWHEEL ===")
    armor = OctoArmor()

    # Simulate some observations
    for prompt, response in [
        ("What is hyperbolic geometry?", "Hyperbolic geometry is a non-Euclidean geometry..."),
        ("Explain the Poincare ball model", "The Poincare ball is an open unit ball where..."),
    ]:
        armor.polly.observe("groq", "llama-3.3-70b", "KO", prompt, response, 100.0)

    flywheel = TrainingFlywheel(armor)
    report = flywheel.daily_report()
    print(report)
    print()

    # Flush to disk
    filepath = flywheel.flush()
    print(f"  Training data flushed to: {filepath}")
    print()


if __name__ == "__main__":
    test_tentacle_status()
    test_free_models()
    test_tokenizer_gateway()
    test_polly_observer()
    test_training_flywheel()

    # Live test — only if any keys are available
    asyncio.run(test_live_reach())
