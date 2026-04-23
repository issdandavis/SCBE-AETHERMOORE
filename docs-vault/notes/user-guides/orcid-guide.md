---
title: ORCID Usage Guide
type: user-guide
created: 2026-04-04
tags: [orcid, research, identity, publishing]
---

# ORCID Usage Guide — SCBE-AETHERMOORE

## What is ORCID?

ORCID (Open Researcher and Contributor ID) is a persistent digital identifier for researchers. It connects you to your research outputs (papers, datasets, patents, code) across all platforms. Think of it as a universal researcher passport.

**Your ORCID:** [0009-0002-3936-9369](https://orcid.org/0009-0002-3936-9369)

## Login

- URL: https://orcid.org/signin
- Use your registered email (issdandavis7795@gmail.com or aethermoregames@pm.me)

## Profile Sections

### Names
- **Primary:** Issac Davis
- **Also known as:** Izack Realmforge, Issac Daniel Davis
- These aliases help people find you if they search under different names

### Biography
- Public-facing description of who you are and what you do
- Edit via the pencil icon next to "Biography"
- Supports markdown-style bold (`**text**`)
- Maximum ~5000 characters

### Websites & Social Links
- Add links to GitHub, HuggingFace, HF Space, personal site
- Each link gets a label (e.g., "GitHub Enterprise", "HuggingFace Space")
- Visibility: set each to "Everyone" (green eye icon) for public

### Keywords
- Searchable tags that help other researchers find you
- Pick terms that match your actual research domains
- Current recommended keywords: AI Safety, Hyperbolic Geometry, Post-Quantum Cryptography, Sacred Tongue Tokenization, Governance Frameworks, Conlang Engineering, Training Data Pipelines, Federated Learning

### Works / Activities
- Add publications, preprints, datasets, patents
- Can import from DOI, arXiv, Crossref, DataCite
- Your HF dataset can be added as a "Data set" work type

## Developer Tools (API Access)

- URL: https://orcid.org/developer-tools
- **Client ID:** APP-9VNR6CYW0IOAWTMW (public, safe to share)
- **Client Secret:** NEVER share this. Rotate if exposed.
- **Redirect URI:** https://aethermoore.com/SCBE-AETHERMOORE/

### OAuth Flow
1. User visits: `https://orcid.org/oauth/authorize?client_id=APP-9VNR6CYW0IOAWTMW&response_type=code&scope=/authenticate&redirect_uri=YOUR_URI`
2. User authorizes → redirected back with `?code=XXXXX`
3. Exchange code for token via POST to `https://orcid.org/oauth/token`

### API Usage
- Public API: read-only, free for non-commercial use
- Member API: read/write, requires institutional membership
- Rate limits: 24 requests/second (public), higher for members

## Where ORCID Connects

| Platform | How to Link |
|----------|-------------|
| **GitHub** | Add ORCID to profile bio or repo README |
| **HuggingFace** | Add to dataset/model card metadata |
| **arXiv** | Link during paper submission |
| **Google Scholar** | Add to profile settings |
| **SAM.gov** | Reference in entity registration |
| **USPTO** | Include in patent applications |

## Maintenance Checklist

- [ ] Update biography when major milestones hit (new patent, dataset size, publications)
- [ ] Add new works (datasets, papers, preprints) as they publish
- [ ] Keep keywords current with actual research focus
- [ ] Verify email domains if possible (adds credibility)
- [ ] Review website links quarterly — remove dead links
- [ ] Rotate client secret annually or if exposed

## Current Update Needs (2026-04-04)

- Biography: "13-Layer" → "14-Layer", PQC algorithm names outdated
- Add: HF Space link, HF dataset link, live demo URL
- Keywords: remove generic ones (Notion, Zapier, SaaS), add research-specific
- Add HF dataset as a "Work" entry
