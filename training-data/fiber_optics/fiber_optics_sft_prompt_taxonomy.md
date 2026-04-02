# Fiber Optics SFT Prompt Taxonomy

These are the first 100 prompt types to seed a specialist adapter on top of the current Qwen lane.

## Trace Classification

1. Identify the primary impairment from an OTDR trace summary.
2. Distinguish splice loss from distributed attenuation on a distance-domain trace.
3. Decide whether a reflection spike indicates a connector issue or a measurement artifact.
4. Classify whether a trace is dominated by attenuation, dispersion, or nonlinear distortion.
5. Identify the most likely failure point from a trace with one abrupt loss step.
6. Compare two traces and explain which link has worse optical health.
7. Infer whether an amplifier stage is masking an underlying loss pattern.
8. Detect whether the trace suggests a bad splice, bad connector, or excessive fiber length.
9. Explain why a clean OTDR trace can still coexist with a poor BER reading.
10. Rank the top three suspected impairments from a mixed trace summary.

## Spectral Interpretation

11. Read a power spectrum summary and identify likely chromatic dispersion.
12. Use FFT-bin summaries to decide whether high-frequency energy loss is significant.
13. Explain what wavelength-dependent broadening implies about link behavior.
14. Distinguish attenuation roll-off from dispersion-induced spreading in spectral form.
15. Infer whether the measured spectrum suggests filter misalignment.
16. Compare two spectral summaries and choose the healthier channel.
17. Explain why spectral narrowing can raise BER even without major power loss.
18. Identify whether the spectrum is consistent with nonlinear effects.
19. Use spectral asymmetry to argue for or against Kerr-driven distortion.
20. Map a spectrum summary to the most likely first mitigation step.

## Phase And Group Delay

21. Identify the dominant impairment from a phase-slope summary.
22. Decide whether group delay variation indicates chromatic dispersion or PMD.
23. Explain why a near-linear phase slope still can produce pulse spreading.
24. Compare two phase summaries and determine which link is harder to equalize.
25. Interpret group-delay measurements in ps as operational risk.
26. Infer whether a phase wrap pattern suggests measurement error or real channel behavior.
27. Explain the operational meaning of a steep group-delay slope.
28. Diagnose whether phase instability is transient noise or structural impairment.
29. Distinguish PMD from CD using phase and polarization evidence together.
30. Recommend the safest next measurement after observing high group delay.

## Polarization And PMD

31. Identify PMD from a polarization-state summary.
32. Explain why PMD can fluctuate even when total power looks stable.
33. Compare chromatic dispersion and PMD in terms of what the trace should show.
34. Decide whether the evidence supports PMD as the primary impairment.
35. Explain how polarization drift can affect BER.
36. Infer whether polarization behavior suggests connector stress or route instability.
37. Describe how PMD differs from simple attenuation in operator-visible symptoms.
38. Rank likely fixes for a PMD-heavy channel.
39. Explain when DSP equalization helps PMD and when it is insufficient.
40. Interpret a PMD measurement in ps/sqrt(km) for operational triage.

## Kerr And Nonlinear Effects

41. Identify a likely Kerr-nonlinearity case from launch power and BER trends.
42. Explain why increasing launch power can worsen signal quality.
43. Distinguish Kerr distortion from attenuation when total power remains high.
44. Diagnose whether nonlinear phase shift is operationally significant.
45. Compare two launch-power scenarios and predict which will have better BER.
46. Explain self-phase modulation in operator language.
47. Infer whether reducing power or changing compensation is the better first move.
48. Decide whether the symptoms point to Kerr effects or amplifier noise.
49. Explain why nonlinear penalties can appear only after a threshold.
50. Recommend a safe nonlinear-mitigation sequence for a field engineer.

## BER, Q-Factor, And Health Metrics

51. Explain why BER increased when attenuation barely changed.
52. Use BER and Q-factor together to identify the dominant issue.
53. Classify whether a BER rise is more consistent with dispersion, PMD, or noise.
54. Compare two Q-factor readings and choose the more robust link.
55. Explain what a low Q-factor means for operator action.
56. Identify the likely failure mode from BER history over time.
57. Infer whether BER spikes suggest transient noise or structural degradation.
58. Explain why good optical power does not guarantee good BER.
59. Map a BER/Q pair to an urgency level.
60. Recommend what to inspect next after a BER jump with stable power.

## Link Budget And Calculation

61. Compute a rough link budget from provided launch power and losses.
62. Decide whether the margin is sufficient for the stated route.
63. Explain which component contributes most to margin loss.
64. Compare two link budgets and identify the riskier design.
65. Estimate whether amplifier gain is masking excessive attenuation.
66. Explain how connector loss compounds across a route.
67. Identify which missing measurement is needed to trust the budget.
68. Compute whether the route can tolerate one extra splice.
69. Explain why link-budget success can still hide dispersion failure.
70. Recommend the first design adjustment when the budget is marginal.

## Remediation Planning

71. Choose the best first remediation for chromatic dispersion.
72. Choose the best first remediation for PMD.
73. Choose the best first remediation for Kerr nonlinearity.
74. Choose the best first remediation for splice loss.
75. Prioritize a remediation plan for mixed attenuation and dispersion.
76. Compare DSP equalization versus physical compensation for a given case.
77. Explain when reducing launch power is smarter than adding amplification.
78. Recommend a field sequence that minimizes service disruption.
79. Explain how to validate whether the remediation worked.
80. Provide a rollback-safe plan for experimenting with compensation settings.

## Comparison And Counterfactuals

81. Compare chromatic dispersion and PMD on the same route.
82. Explain how the diagnosis changes if launch power were 3 dB lower.
83. Predict what the trace would look like if the issue were attenuation instead of PMD.
84. Explain what would change if the BER stayed low despite the same trace.
85. Compare two remediation plans and choose the lower-risk option.
86. Explain why one impairment can masquerade as another.
87. Identify the minimum evidence needed to separate Kerr effects from amplifier noise.
88. Compare two channels and explain why one is more future-proof.
89. Predict the operator-visible effect of removing dispersion compensation.
90. Explain what new failure mode becomes dominant after attenuation is fixed.

## Governance And Specialist Routing

91. Decide whether the case is safe for automatic remediation or needs human escalation.
92. Explain why the current evidence is insufficient for a confident diagnosis.
93. Produce a confidence-scored diagnosis with explicit caveats.
94. Decide whether the record belongs in train, validation, or test split.
95. Identify which view (`L0`, `L1`, `L2`, `L3`) is missing and why that matters.
96. Explain whether the example is better suited for SFT or DPO follow-up.
97. Rank the case by training value for a fiber specialist adapter.
98. Convert a prose-only optics explanation into a multiview packet plan.
99. Decide whether the impairment evidence supports one dominant answer or a mixed diagnosis.
100. Explain when to route the case to the general governance model versus the fiber specialist adapter.

## Build Order

Recommended order for the first 100 records:

- `1-20`: easy trace and spectrum recognition
- `21-40`: phase and polarization discrimination
- `41-60`: nonlinear and BER/Q interpretation
- `61-80`: calculations and remediation planning
- `81-100`: counterfactuals, routing, and governance-style uncertainty handling
