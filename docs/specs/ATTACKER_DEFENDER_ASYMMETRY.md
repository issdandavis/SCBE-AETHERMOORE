# Chapter 3: Attacker vs Defender Asymmetry

This chapter proves the economic and computational advantage defenders gain using SCBE.

## Core Asymmetry

- Defender cost: O(1) constant time to verify
- Attacker cost: O(R^(d*^2)) super-exponential in deviation
- At d*=0.99: attacker pays ~10,000x more than defender

## Why This Matters

Traditional security is symmetric — attackers find ONE vulnerability, defenders must protect EVERYTHING.

SCBE is asymmetric — geometric amplification makes unauthorized behavior inherently expensive, not just "detected and blocked."

## Economic Model

Attack cost at distance d* with K=3 (triple-sig), R=10, D=12 dimensions:
- Cost ratio: (K * R^(d*^2)) / D
- At d*=0.9: ratio = 158:1 (attacker needs 158x more resources)

## Gradual Escalation Example (R=10)

| Step | Distance | Cost | Cumulative |
|------|----------|------|------------|
| Start | 0.9 | R^0.81 = 631 | 631 |
| Step 2 | 0.8 | R^0.64 = 251 | 882 |
| Step 3 | 0.7 | R^0.49 = 100 | 982 |
| Step 4 | 0.6 | R^0.36 = 40 | 1,022 |
| Step 5 | 0.5 | R^0.25 = 16 | 1,038 |
| Step 6 | 0.4 | R^0.16 = 6 | 1,044 |

Total attack: 1,044 operations. Defender: 6 verifications. Asymmetry: 174:1.

## Key Insight

The geometry itself is the defense. No rules to break. No signatures to forge. The space makes unauthorized movement exponentially expensive.

Source: Notion page 2d7f96de-82e5-81a7-9f50-ec0b01e35469 (January 26, 2026)
