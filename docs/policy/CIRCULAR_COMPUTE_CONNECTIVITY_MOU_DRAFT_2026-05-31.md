# Circular Compute Connectivity MOU Draft

Working draft: 2026-05-31

Status: SCBE-owned policy concept and implementation appendix. This is not a signed agreement, not procurement advice, and not a claim that SpaceX, Starlink, Commerce, GSA, FCC, USDA, or any other party has accepted these terms.

## Purpose

This memorandum of understanding framework describes how the National Circular Compute Program could procure satellite, terrestrial, or hybrid connectivity for Circular Compute Nodes deployed on federal, state, tribal, university, or public-partner sites.

The draft is written as a provider-neutral implementation rider. Starlink is used as the first reference provider because Starlink has public government purchasing and civil government service pathways, but the same structure should remain available to other qualified low-Earth-orbit, fixed wireless, fiber, or hybrid providers.

## Parties

Federal lead:

- U.S. Department of Commerce, acting through the National Circular Compute Program.

Coordinating agencies:

- National Science Foundation.
- Department of Energy.
- Department of Labor.
- National Institute of Standards and Technology.
- General Services Administration.
- Other agencies designated by statute or interagency agreement.

Connectivity provider:

- A qualified commercial connectivity provider selected through lawful procurement. Example reference provider: Space Exploration Technologies Corp., acting through Starlink or Starshield-compatible government service channels where legally appropriate.

## Scope of Services

The provider shall support deployed Circular Compute Nodes with connectivity, installation training, service monitoring, and audit records sufficient for public infrastructure use.

Proposed service responsibilities:

1. Supply approved ground terminals, routers, mounting kits, cabling, spares, and firmware update processes.
2. Provide site connectivity for Circular Compute Nodes in rural, remote, disaster-prone, or fiber-limited locations.
3. Support private routing or traffic segregation where available.
4. Train Digital Infrastructure Corps apprentices on safe installation, alignment, basic troubleshooting, power tolerances, and escalation procedures.
5. Maintain service-level reporting for uptime, latency, throughput, outage windows, and service restoration.

## Procurement Posture

The preferred procurement posture is commercial-first and provider-neutral.

Possible lawful vehicles to evaluate:

- GSA Multiple Award Schedule purchasing where applicable.
- Commercial Solutions Opening.
- Other Transaction Authority where legally available for the sponsoring agency.
- Existing broadband, emergency communications, rural connectivity, or public-sector service agreements.
- Competitive blanket purchase agreements for multiple qualified providers.

Validation needed: counsel and procurement officers must confirm which vehicle is lawful for the final program, funding source, and deployment site type.

## Service-Level Targets

The following values are proposed targets, not verified contract terms:

| Target | Draft Value | Validation Need |
| --- | ---: | --- |
| Minimum downlink per active node | 100-150 Mbps | Verify provider plan, contention, weather impact, and site geography. |
| Minimum uplink per active node | 20-40 Mbps | Verify provider plan and workload profile. |
| Latency | 40-80 ms target range | Validate per site and avoid overpromising percentile guarantees. |
| Uptime | 99.5-99.9% target range | Confirm whether provider SLA exists for the selected plan. |
| Outage reporting | Monthly plus incident-level events | Define format for agency and GAO review. |
| Emergency restoration | Priority queue where available | Confirm with provider and emergency authorities. |

The program should avoid publishing a hard 99th-percentile latency or 99.9% uptime promise until an executed provider agreement supports it.

## Data Sovereignty and Privacy

The provider shall operate as a transport layer and shall not inspect, monetize, train on, sell, or retain user query content except as required for lawful transport, cybersecurity, fraud prevention, sanctions compliance, or court order.

Minimum data requirements:

1. User content remains encrypted end to end between the user device, government-managed endpoint, and Circular Compute Node.
2. Government-furnished keys remain under government or authorized program control.
3. Provider logs are limited to routing, performance, billing, abuse prevention, and security metadata.
4. Provider may not use user content or inference outputs for commercial model training or advertising.
5. Routing records sufficient for audit shall be provided to Commerce and GAO under protected handling rules.

U.S.-only routing should be an objective where technically and legally available. It should not be represented as guaranteed until confirmed by the provider's network architecture and contract.

## Traffic Architecture

The target architecture separates user content, node telemetry, and administrative control planes.

### User Compute Plane

The user compute plane carries encrypted prompts, tool requests, inference outputs, and session metadata. It should use government-managed encryption and runtime governance controls.

### Node Telemetry Plane

The telemetry plane carries non-content operational data:

- Battery state.
- Solar generation.
- Thermal status.
- Cooling pump and fan health.
- Terminal status.
- Uptime and outage records.
- Physical tamper alerts.

Telemetry may be visible to Reclaim Labs and maintenance teams, but should not include user content.

### Administrative Plane

The administrative plane handles firmware updates, node certificates, model image updates, policy updates, and incident response. Updates should be signed, logged, and staged during low-demand windows where possible.

## Pricing Framework

The following values are a 2026 planning zone from public government/commercial pricing, not negotiated program pricing.

### Starlink Government Schedule Zone

Public GSA schedule data for SpaceX MAS Contract 47QRAA21D007N lists the Starlink Flat High Performance Kit at about $2,569 one-time. The same schedule lists annual fixed-site Priority service packages at about $3,023/year for 1TB/month, $6,045/year for 2TB/month, and $18,136/year for 6TB/month. Mobile Priority is substantially more expensive at high data tiers, reaching about $60,453/year for 5TB/month.

That means Grok's proposed $650 terminal and $1,800/year service should be treated as a negotiation target or future bulk-discount scenario, not as the current government-market baseline.

### Per-Node Connectivity Zones

| Item | Draft Planning Range |
| --- | ---: |
| Low public/commercial baseline | $300-$600 standard terminal; $600-$1,500/year service; only suitable for light or non-SLA public access. |
| Fixed government Starlink baseline | About $2,569 terminal; about $3,023-$6,045/year for 1-2TB/month Priority. |
| Higher-demand fixed node | About $2,569 terminal; about $18,136/year for 6TB/month Priority. |
| Mobile/emergency node | About $2,569 terminal; about $3,023-$60,453/year depending on 50GB-5TB Mobile Priority tier. |
| GEO satellite backup | About $600-$1,400 equipment for basic fixed business service, but often lower speed and higher latency. |
| Managed/flyaway government SATCOM | About $19,000-$35,000 hardware for some deployable systems, before travel and integration. |
| Training package | Negotiated per cohort or included in national service agreement. |
| Replacement spares | 5-15% of deployed terminal count annually. |

### Working Budget Rule

For the whitepaper, use these conservative planning assumptions:

- Base fixed node: $2,600 hardware plus $3,100-$6,100/year service.
- Heavy fixed node: $2,600 hardware plus about $18,200/year service.
- Emergency/mobile node: $2,600 hardware plus $12,100-$60,500/year service if mobility and high priority data are required.
- Bulk-discount target: $1,000-$2,500 hardware plus $1,800-$3,000/year service, only after provider negotiation.

At 1,800 fixed nodes, the first-year Starlink-style government baseline is approximately:

- 1TB fixed priority: $10.1 million first year, then $5.4 million/year service.
- 2TB fixed priority: $15.5 million first year, then $10.9 million/year service.
- 6TB fixed priority: $37.3 million first year, then $32.6 million/year service.

These ranges still fit inside a $323 million annual reserve, but they are materially higher than the $4.5 million/year claim in the Grok draft unless a bulk discount is negotiated.

The final public whitepaper should use ranges until quote-backed values are obtained from providers, GSA listings, reseller schedules, or executed contracts.

## Apprenticeship and Workforce Integration

The provider should support the Digital Infrastructure Corps through:

1. Annual installation and maintenance training.
2. Train-the-trainer modules for university Reclaim Labs.
3. Safety guidance for roof, pole, ground-mount, enclosure, and battery-adjacent installations.
4. Documentation suitable for community-college and trade-school instruction.
5. Preferential interview or hiring pathways where lawful and nonexclusive.

Training commitments should be nonexclusive so apprentices learn general satellite and network installation skills, not only a single vendor's product.

## Emergency Operations

During declared emergencies, the program may activate an emergency operations profile.

Emergency profile capabilities:

- Prioritize emergency communications, public service queries, local logistics, and civil authority dashboards.
- Suspend nonessential public compute workloads.
- Isolate compromised nodes.
- Route around damaged infrastructure where provider capability permits.
- Preserve audit logs for post-incident review.

Emergency override authority must be defined by statute, executive authority, or agency operating procedure. It should include a time limit, review process, and civil-liberties safeguards.

## Ownership and Termination

Draft termination model:

- Initial term: 5 years, with renewal options.
- Termination for cause: material breach, persistent SLA failure, cybersecurity breach, sanctions violation, or national-security determination.
- Termination for convenience: allowed if required by federal procurement rules, with a transition period.
- Hardware ownership: determined by purchase vehicle. Government-owned terminals should remain government property. Provider-owned terminals should have a transfer or buyout clause where economically justified.

Avoid promising no-cost transfer of all deployed terminals unless the contract pricing explicitly includes that term.

## Liability and Content Boundaries

The provider is not responsible for model behavior, content moderation, public access eligibility, governance decisions, or user-facing policy decisions made by the Circular Compute Program.

The Circular Compute Program is not responsible for provider network design choices except as accepted through procurement, audit, and service monitoring.

Both parties must preserve incident records for cybersecurity, privacy, uptime, and safety investigations.

## Metrics for GAO and Public Reporting

Reportable connectivity metrics:

- Nodes connected by provider and region.
- Monthly uptime per node.
- Median and p95 latency per node.
- Median and p95 throughput per node.
- Outage count and duration.
- Emergency-mode activations.
- Data-sovereignty incidents.
- Privacy incidents.
- Cybersecurity incidents.
- Cost per connected node per month.
- Apprentice training completions.

Public reports should aggregate sensitive security and routing details to avoid exposing attack surfaces.

## Open Validation Items

Before external publication, validate:

1. Actual Starlink, Starshield, or other provider government pricing.
2. Whether selected service plans provide enforceable SLA terms.
3. Whether U.S.-only routing is technically enforceable.
4. Whether provider logs can meet GAO audit needs without exposing user content.
5. Which procurement vehicles are lawful for Commerce-led deployment.
6. Whether BEAD, High-Cost Fund, USDA, or other broadband authorities can fund node connectivity rather than residential broadband alone.
7. Whether emergency override language needs separate statutory authorization.
8. Whether single-provider language creates avoidable procurement or antitrust risk.

## Source Anchors

- Starlink civil government support page: https://starlink.com/support/article/3ccad59e-9525-9492-9835-d1945a4ee30f
- Starlink U.S. government purchasing support page: https://starlink.com/xk/support/article/e1744a37-1747-565d-c93c-9bd9afff9e48
- SpaceX GSA MAS public pricelist, Contract 47QRAA21D007N: https://www.gsaadvantage.gov/ref_text/47QRAA21D007N/0ZL0AE.3VBD52_47QRAA21D007N_PRICELIST20240722.PDF
- Hughes Texas DIR telecom pricing appendix: https://www.hughes.com/wp-content/uploads/2026/01/DIR-TELE-CTSA-007-Carrier-Class-B-2-Pricing-EAU-7.pdf
- Viasat GSA pricelist: https://www.viasat.com/content/dam/us-site/government/documents/GSA_Pricelist_Mod63.pdf
- FCC Starlink and supplemental coverage materials: https://docs.fcc.gov/public/attachments/DA-26-398A1.pdf
- Apprenticeship.gov apprenticeship system overview: https://www.apprenticeship.gov/about-us/apprenticeship-system
