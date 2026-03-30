---
title: "64.8% Energy Savings: How a Governance Cost Function Doubles as a Compute Governor"
published: false
description: "The same harmonic cost function that blocks prompt injection also cuts AI compute energy by 64.8%. Tested on real Kaggle microgrid data. Open source."
tags: ai, energy, sustainability, machinelearning
canonical_url: https://aethermoorgames.com/research/compute-governor.html
---

## The Accidental Discovery

We built a cost function to block prompt injection attacks on AI systems. The function is simple:

```
H(d*, R) = pi^(phi * d*)
```

Where `d*` is the distance from a known-safe baseline and `phi` is the golden ratio (1.618). Safe actions cost almost nothing. Dangerous actions cost exponentially more.

Then we pointed it at energy management. Same function. No changes.

**Result: 64.8% energy savings on real microgrid data.**

## How It Works

The system sits between an AI inference request and the execution backend. Every workload is classified into four tiers:

| Tier | Model Size | Power Draw | When Used |
|------|-----------|------------|-----------|
| TINY | < 1B params | 5-15 W | Classification, routing, keyword extraction |
| MEDIUM | 1-7B params | 50-120 W | Summarization, structured output, RAG |
| FULL | 7-70B+ params | 200-700 W | Complex reasoning, code generation, agents |
| DENY | N/A | 0 W | Thermal limit exceeded or budget exhausted |

The same cost function that measures "how far is this action from safe?" now measures "how far is this workload from cheap?" Safe and cheap share the same math -- they both mean "close to the baseline."

## Real Numbers (Not Synthetic)

We ran a 24-hour simulation using the Kaggle Renewable Energy Microgrid Dataset (3,546 real hourly readings with solar, battery, and grid data):

- **1,000 workloads** across 24 hours
- **Energy consumed**: 0.92 kWh (baseline: 2.62 kWh)
- **Peak demand**: 9,899 W (baseline: 30,600 W)
- **Grid cost**: $0.15 (baseline: $0.42)
- **Thermal events prevented**: 2 (auto-denied when cooling failed)
- **Tier distribution**: 27% TINY, 37% MEDIUM, 30% FULL, 6.4% DENY

The system routes 64% of requests to cheaper tiers without degrading output quality, because most inference requests don't need a 70B model.

## Why This Matters (DOE Context)

The U.S. Department of Energy projects data center electricity consumption will rise from 4.4% to 12% of national demand by 2028. AI workloads are the primary driver. Current inference pipelines have no built-in power budget enforcement.

This system adds one: a mathematically grounded authorization layer that says "you can't run a 70B model when the battery is at 10% and cooling is offline."

## The API

```python
import requests

response = requests.post(
    "https://your-domain.com/v1/compute/authorize",
    json={
        "description": "Summarize this report",
        "model_size_params": 1.5,
        "estimated_tokens": 500,
        "energy_state": {
            "available_wh": 50,
            "source": "solar",
            "battery_pct": 65,
            "solar_forecast_wh": 30,
            "cooling_available": True
        }
    }
)
tier = response.json()["tier"]  # "MEDIUM"
```

## The Deeper Point

The cost function wasn't designed for energy. It was designed for security. The fact that it works for both -- without modification -- suggests the underlying principle is general: **cost should scale exponentially with distance from known-safe operation**, regardless of what "safe" means in context.

## Links

- **Full simulation data**: [Kaggle Dataset](https://kaggle.com/datasets/issacizrealdavis/scbe-governance-research-results)
- **Research page**: [Compute Governor](https://aethermoorgames.com/research/compute-governor.html)
- **Source code**: [GitHub](https://github.com/issdandavis/SCBE-AETHERMOORE)
- **Training data + model**: [HuggingFace](https://huggingface.co/datasets/issdandavis/scbe-aethermoore-training-data)

---

*Built by Issac Daniel Davis. SCBE-AETHERMOORE is open source under MIT license.*
