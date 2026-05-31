# National Circular Compute and Tech Apprenticeship Act

Working draft: 2026-05-31

Status: SCBE-owned policy concept and whitepaper draft. This is not a filed bill, not legal advice, and not a claim that any federal program currently provides public citizen AI compute.

## Executive Summary

The National Circular Compute and Tech Apprenticeship Act proposes a public-interest compute network built from reclaimed enterprise hardware, university and community-college refabrication labs, registered apprenticeship pathways, renewable micro-infrastructure, and secure cross-platform AI access.

The core idea is simple: stop treating decommissioned compute, returned hardware, military surplus infrastructure, vehicle cooling parts, and student engineering labor as disconnected leftovers. Bind them into a circular national system that turns waste into useful local AI capacity, workforce training, rural resilience, and auditable public infrastructure.

This proposal is designed as a pragmatic extension of existing public infrastructure lanes rather than a new open-ended entitlement. It uses existing federal IT procurement, CHIPS/NSTC semiconductor infrastructure, NAIRR-style AI resource access, Department of Labor apprenticeship mechanisms, and commercial satellite connectivity where terrestrial fiber is not practical.

## Problem

AI access is increasingly becoming a baseline economic tool, but practical access remains uneven. Citizens, students, small businesses, rural communities, public libraries, and local governments often lack affordable compute, trusted governance, and durable infrastructure.

At the same time, the United States produces large volumes of decommissioned enterprise hardware, surplus public equipment, returned components, vehicle scrap, and electronics waste. Much of this material is destroyed, auctioned, exported, or left outside any public-value loop.

The production gap is not only a model gap. It is an infrastructure, workforce, governance, and lifecycle gap.

## Program Design

The Act establishes a National Circular Compute Program with four loops.

### 1. Hardware Loop

Corporate IT asset disposition streams, federal surplus systems, returned hardware, retired military enclosures, vehicle radiators, EV battery modules, copper busbars, and electronics scrap are routed into approved Reclaim Labs.

Reclaim Labs test, repair, certify, and refabricate usable components into Circular Compute Nodes. The nodes are not intended to train frontier models. They provide governed inference, CLI tooling, web-based assistance, local public service routing, and resilient emergency support.

### 2. Workforce Loop

The Digital Infrastructure Corps creates paid, credit-bearing apprenticeship pathways for college, community-college, trade-school, and veteran trainees. Apprentices work on hardware testing, silicon reclaim, PCB repair, secure networking, cooling loops, battery safety, deployment operations, and node maintenance.

The model should use paid stipends. It should not rely on unpaid student labor.

### 3. Access Loop

The public access system follows a library-style model:

- Registered voters receive free basic-tier access.
- Adults 18 and older receive basic eligibility, including students who are not registered voters.
- Minors access the system through guardian, school, or library-card-style opt-in.
- Non-citizens, international researchers, and humanitarian users use separate research, education, disaster-response, or paid channels.

Access should be device-agnostic: CLI, web, mobile, and API where appropriate.

### 4. Funding Loop

The program is funded through circular procurement rather than a new broad tax. A percentage set-aside inside existing federal IT hardware procurement budgets funds Reclaim Labs, node deployment, hardware intake, software governance, and independent audits.

Draft CBO-protective language:

> The set-aside shall be administered within each federal agency's existing IT hardware procurement budget and shall not increase overall appropriations unless separately authorized by Congress.

## Technical Architecture

### Circular Compute Node

A Class-II Circular Compute Node is a rugged, renewable-powered local inference system built from reclaimed and refabricated parts.

Expected components:

- Reclaimed enterprise GPUs or accelerator cards from corporate returns, public surplus, or cloud refresh cycles.
- Server-grade CPUs, memory, and self-encrypting SSDs from certified ITAD channels.
- Military-grade or industrial enclosures for weather resistance and physical durability.
- Refabricated cooling loops using automotive radiators, pumps, copper plates, and monitored fluid systems.
- Renewable power plus battery storage, with low-power fallback mode for emergencies.
- Satellite or terrestrial connectivity, selected by site.

Important boundary: old consumer PCs and vehicle microcontrollers are not treated as primary AI accelerators. They can support enclosure, power, cooling, monitoring, and training workflows, but modern AI inference still depends on suitable enterprise silicon and memory bandwidth.

### Connectivity

Remote nodes may use commercial low-Earth-orbit satellite broadband when fiber or fixed wireless is unavailable. Starlink is one possible provider because it has government purchasing paths and civil government service options, but the policy should remain provider-neutral.

Provider-neutral language:

> The Secretary of Commerce may establish one or more commercial satellite or terrestrial connectivity agreements for Circular Compute Nodes, provided that each provider operates as a transport layer only and complies with program data-sovereignty, privacy, uptime, and audit requirements.

### Governance and Runtime Controls

All nodes should include approved governance frameworks for safe and auditable AI inference. Minimum controls:

- Runtime authorization before tool execution.
- Tiered command decisions such as ALLOW, QUARANTINE, ESCALATE, and DENY.
- Tamper detection and cryptographic event logs.
- Separation between system telemetry and user content.
- Transparent incident reporting.
- Content-neutral, viewpoint-neutral access rules modeled on public libraries and community colleges.

SCBE can fit this lane as a governance SDK, audit layer, or runtime control package, but the policy text should avoid naming one vendor or one internal system.

## Draft Legislative Skeleton

### Section 1. Short Title

This Act may be cited as the "National Circular Compute and Tech Apprenticeship Act."

### Section 2. Findings and Purpose

Congress finds that AI compute, secure digital literacy, semiconductor workforce development, electronics waste reduction, rural resilience, and public access to basic digital infrastructure are matters of national interest.

The purpose of this Act is to create a circular compute system that reclaims public and private hardware waste, trains a domestic refabrication workforce, deploys resilient local inference infrastructure, and provides governed basic AI access for eligible public users.

### Section 3. Definitions

"Circular Compute Node" means a decentralized compute system using reclaimed or refabricated hardware, renewable or resilient power, secure networking, and approved governance controls.

"Reclaim Lab" means a university, community-college, trade-school, or public-private facility that tests, repairs, certifies, and refabricates components for Circular Compute Nodes.

"Digital Infrastructure Corps" means a paid apprenticeship and training pathway aligned with registered apprenticeship standards and local education credit systems.

### Section 4. National Circular Compute Program

The Secretary of Commerce, in coordination with NSF, DOE, DOL, NIST, GSA, and other appropriate agencies, shall establish a program to deploy Circular Compute Nodes, fund Reclaim Labs, and operate a secure public access system.

### Section 5. Reclaim Labs and Apprenticeship

Competitive grants shall support Reclaim Labs with priority for land-grant universities, community colleges, trade schools, rural-serving institutions, veteran-serving programs, and institutions with existing semiconductor, electronics, or cleanroom capacity.

### Section 6. Circular Compute Nodes

Nodes shall prioritize reclaimed enterprise silicon, federal surplus infrastructure, renewable power, safe battery storage, and auditable runtime controls. Nodes shall support basic-to-mid-tier inference and public service workflows, not unrestricted frontier-model training.

### Section 7. Public Access

Access shall operate under content-neutral, viewpoint-neutral policies modeled on public libraries and community colleges, with minimal moderation limited to illegal activity, system abuse, safety risk, and transparent appeal processes.

### Section 8. Connectivity

The program may procure satellite, terrestrial, or hybrid connectivity through commercial agreements, GSA schedules, or other lawful procurement vehicles. Connectivity providers shall not inspect, monetize, train on, or retain user query content beyond what is required for lawful transport and security operations.

### Section 9. Oversight

Annual reports shall include:

- Nodes deployed.
- Reclaim Labs funded.
- Apprentices trained and placed.
- E-waste diverted in metric tons.
- Energy consumed and generated per node.
- Uptime and emergency-mode activations.
- Governance incidents logged.
- Cost per public compute hour.
- Privacy and cybersecurity incidents.

GAO shall audit the program at least every two years. The program sunsets after ten years unless reauthorized.

## Budget Model To Validate

The transcript draft suggested a per-lab model of roughly:

- Year-1 CapEx: about $610,000.
- Annual OpEx: about $570,000.
- Apprentices per lab: 20.
- Target output: 12 nodes per lab per year.
- National scale: 150 labs.

These are useful planning placeholders, but they should not be published as confirmed estimates until validated against current equipment quotes, institutional overhead rules, safety requirements, labor rates, hazardous-material handling, insurance, federal acquisition costs, and connectivity pricing.

## Claims Posture

Verified anchors as of 2026-05-31:

- NAIRR exists as an AI resource access initiative focused on researchers, educators, students, and innovators, not as a universal citizen AI utility.
- NSF and Commerce/NIST have CHIPS/NSTC-related semiconductor research and workforce infrastructure.
- Registered Apprenticeship is a Department of Labor system with established registration, oversight, and funding pathways.
- Starlink offers civil government and federal purchasing paths, but policy text should remain provider-neutral.

Assumptions requiring further validation:

- Exact e-waste volume available through federal and corporate intake streams.
- Actual yield rate of usable enterprise GPUs from returns and decommissioned data centers.
- Safety and legality of using salvaged automotive cooling and EV battery modules in unattended federal micro-data-center deployments.
- Node throughput, concurrency, and cost-per-token.
- Starlink or other provider bandwidth guarantees, data-sovereignty terms, and federal pricing.
- Legal viability of voter-linked access and equal-protection boundaries.

## SCBE Product Hook

SCBE should not pitch this as "free AI handouts." The commercially useful angle is:

> SCBE provides the governance, runtime authorization, audit evidence, and cross-agent coordination layer that lets circular public compute nodes operate safely across CLI, web, mobile, and API surfaces.

Near-term product surfaces:

- Governance SDK for node runtime authorization.
- REST endpoint for public or institutional apps.
- Dashboard generator for node health, governance incidents, access tiers, and audit logs.
- Agent-bus integration for cross-platform task routing.
- Compliance package for universities, public agencies, and contractors.

## Next Work

1. Build a source-backed fact matrix with official sources and dated access notes.
2. Replace placeholder costs with quote-backed ranges.
3. Produce one technical node spec with conservative low, expected, and high capacity bands.
4. Draft a provider-neutral connectivity MOU.
5. Draft a one-page policymaker brief and a two-page university partner brief.
6. Map SCBE modules to the governance and runtime sections without overclaiming exclusivity.

## Source Anchors

- NSF NAIRR update, "NAIRR at 2 years": https://www.nsf.gov/cise/updates/nairr-2-years-advancing-american-artificial-intelligence
- NSF NAIRR pilot page: https://www.nsf.gov/geo/updates/national-artificial-intelligence-research-resource-nairr
- NSF CHIPS and Science page: https://www.nsf.gov/chips
- NIST National Semiconductor Technology Center page: https://www.nist.gov/chips/research-development-programs/national-semiconductor-technology-center
- Apprenticeship.gov system overview: https://www.apprenticeship.gov/about-us/apprenticeship-system
- Department of Labor apprenticeship topic page: https://www.dol.gov/general/topic/training/apprenticeship
- Starlink civil government support page: https://starlink.com/support/article/3ccad59e-9525-9492-9835-d1945a4ee30f
- Starlink U.S. government purchasing support page: https://starlink.com/xk/support/article/e1744a37-1747-565d-c93c-9bd9afff9e48
