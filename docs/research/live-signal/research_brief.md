# Research Signal source brief

Question: Which public, attributable sources can support an automatically refreshed AetherMoore discovery page without credentials, scraping article bodies, or hiding upstream failures?

- Review date: 2026-08-20
- Time window: rolling current feed, with Crossref metadata limited to works published during the previous 90 days
- Geography: worldwide reporting, plus global scholarly metadata and a primary US space-agency lane
- Display boundary: titles, short feed-provided descriptions, dates, source context, and direct original URLs only

## Selected source buckets

1. Established reporting: BBC World, Al Jazeera, Le Monde International, and NPR World. All four public RSS endpoints returned HTTP 200 during the 2026-08-20 operational probe.
2. Primary/niche: NASA's official recent-content RSS feed. NASA's RSS directory identifies this as a supported subscription surface.
3. Academic metadata: arXiv's official Atom API and Crossref's public JSON REST API. The site presents these as discovery metadata, not peer-review or truth scores.

## Rejected primary-path sources

- GDELT DOC 2.0 supports article-list JSON, but the operational probe returned HTTP 429. It is not used in the production source braid.
- ReliefWeb API v2 is read-only and curated, but its current documentation requires a pre-approved app name. The `aethermoore.com` probe returned HTTP 403, so it is not used.

## Confidence

High confidence that the selected endpoints are legitimate public discovery surfaces. Medium confidence in uninterrupted availability: every upstream can fail or change independently. The implementation therefore uses a fixed allowlist, per-source timeouts, ten-minute shared caching, visible health states, and partial success.
