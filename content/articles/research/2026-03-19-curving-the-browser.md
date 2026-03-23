# Curving the Browser: Hyperbolic Trust Surfaces for Web Mediation

**Issac Davis**  
SCBE-AETHERMOORE research draft  
March 19, 2026

## Abstract

Browsers already enforce trust boundaries, but they usually present those boundaries in flat yes-or-no terms. A page is secure or not, a capability is granted or denied, a domain is same-origin or cross-origin. SCBE's browser work asks a different question: what if the browser exposed trust as a geometry instead of a binary? This article situates that idea against official web security standards and the current AetherBrowser code paths, then argues for a mediated model where reading, previewing, attenuating, and committing are distinct states.

## The standards baseline

The W3C Secure Contexts specification defines secure contexts so that user agents and specification authors can restrict sensitive features to contexts meeting minimum standards of authentication and confidentiality. It also makes an important point that secure delivery is a necessary precondition, not a complete guarantee. NIST's Zero Trust Architecture guidance makes a parallel move on the enterprise side: there is no implicit trust based on location, and access should be granted when the resource is required rather than assumed from network position.

That combination already suggests a richer browser model than a lock icon.

If secure delivery is necessary but incomplete, and if trust should be resource-specific rather than location-derived, then a browser could expose more of the trust surface to the user and to AI agents acting inside it.

## The SCBE browser idea

The internal SCBE browser work already contains several building blocks:

- [src/aetherbrowser/topology_engine.py](C:/Users/issda/SCBE-AETHERMOORE/src/aetherbrowser/topology_engine.py)
- [src/aetherbrowser/page_analyzer.py](C:/Users/issda/SCBE-AETHERMOORE/src/aetherbrowser/page_analyzer.py)
- [src/aetherbrowser/phase_tunnel.py](C:/Users/issda/SCBE-AETHERMOORE/src/aetherbrowser/phase_tunnel.py)
- [src/browser/hyperbolicTrustBrowser.ts](C:/Users/issda/SCBE-AETHERMOORE/src/browser/hyperbolicTrustBrowser.ts)

These files move toward a browser that does three things.

First, it analyzes a page as a topology instead of only as a URL.

Second, it represents trust movement in a bounded hyperbolic space rather than as one scalar score.

Third, it allows more outcomes than allow or deny. The current work includes preview-like and attenuation-oriented patterns, including the phase-tunnel idea: inspect without fully committing.

## Why geometry helps

A flat browser interface compresses too many states:

- safe to load
- safe to read
- safe to submit
- safe to execute
- safe to delegate to an agent

Those are not equivalent.

SCBE's geometry approach tries to separate them. A target can be near enough to inspect but still too risky to execute against. A page can be rendered as a visible trust surface where boundary pressure, interaction pressure, and semantic direction are inspectable before action.

That aligns with the logic already present in W3C Secure Contexts. The specification is not only about whether a resource was delivered over HTTPS. It is also about how ancestry, embedding, and powerful-feature exposure affect whether a context should count as secure.

SCBE extends that logic from standards enforcement to operator experience.

## Phase-read instead of full entry

The most useful SCBE browser idea is not exotic math. It is the operational distinction between preview and commitment.

In practical terms, a red-zone link should not force an all-or-nothing decision if the system can safely support:

- metadata view
- preview extraction
- summary-only reading
- blocked execution

That matters for both human and agentic browsing. Many risky pages are risky because of what they ask the browser to do, not because every byte of visible text is intrinsically forbidden to inspect.

This is where the phase-tunnel metaphor becomes operational. The system can let a user or agent inspect a constrained projection of risky space without granting full action rights inside that space.

## What is implemented versus proposed

Implemented in the repo today:

- topology computation for page analysis
- page-analysis summaries and topology payloads
- phase-tunnel code paths
- red-zone integration tests and topology rendering work in the AetherBrowser lane

Still proposed or only internally benchmarked:

- large-scale real-world browsing evaluation
- user studies showing better decision quality than standard browser chrome
- comparison against existing enterprise browser isolation products

So the careful claim is not that the curved browser is already superior in the wild. The careful claim is that the repo now contains a concrete mediation model worth testing against standard browser UX and policy engines.

## Research direction

The next rigorous comparison would measure three browsing workflows across the same risky corpus:

- binary allow/deny
- conventional policy filtering
- topology plus phase-read mediation

The dependent variables should be concrete:

- successful safe information extraction
- accidental execution or submission events
- operator latency
- confidence calibration

If the geometry view improves useful information access without increasing harmful commits, then it is doing something flat browser chrome does not.

## Sources

### Official external sources

- W3C Secure Contexts: https://www.w3.org/TR/secure-contexts/
- NIST SP 800-207 Zero Trust Architecture: https://csrc.nist.gov/pubs/sp/800/207/ipd

### Internal SCBE sources

- [src/aetherbrowser/topology_engine.py](C:/Users/issda/SCBE-AETHERMOORE/src/aetherbrowser/topology_engine.py)
- [src/aetherbrowser/page_analyzer.py](C:/Users/issda/SCBE-AETHERMOORE/src/aetherbrowser/page_analyzer.py)
- [src/aetherbrowser/phase_tunnel.py](C:/Users/issda/SCBE-AETHERMOORE/src/aetherbrowser/phase_tunnel.py)
- [src/browser/hyperbolicTrustBrowser.ts](C:/Users/issda/SCBE-AETHERMOORE/src/browser/hyperbolicTrustBrowser.ts)
