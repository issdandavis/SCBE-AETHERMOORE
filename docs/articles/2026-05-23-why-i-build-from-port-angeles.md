---
title: "Why I Build from Port Angeles"
slug: why-i-build-from-port-angeles
date: 2026-05-23
author: Issac Daniel Davis
tags: [personal, self-taught, port-angeles, origin, scbe, solo-founder]
platforms: [dev.to, aethermoore.com/articles]
status: ready
---

# Why I Build from Port Angeles

Port Angeles, Washington. Population ~20,000. Olympic Peninsula, on the water, facing Vancouver Island across the Strait of Juan de Fuca. PNNL-Sequim is 25 minutes east. The nearest city that a tech recruiter would recognize as a tech city is Seattle, four hours by ferry if conditions are good.

I build AI governance infrastructure here. I'm writing this from a Wendy's.

I don't mention this to perform humility. I mention it because the location shapes how I think about what I'm building and for whom.

---

## No pipeline

The standard path in ML/AI research runs through a PhD program, a lab, a company with compute, a network of people who went to the same conferences. Those institutions are in specific cities. They have application processes. They have prerequisite credentials.

I have one semester of high school programming. No formal CS training. No formal math training beyond what you'd get in a standard public school sequence. Whatever mathematical intuition I have — and some of it turns out to be real, which is still slightly surprising — I built from YouTube, from following chains of citations, from trying things and watching them fail.

The SCBE pipeline independently derived Lyapunov stability analysis, control barrier functions, and port-Hamiltonian energy conservation before I had names for them. I found the names later. That's backwards from how the pipeline is supposed to work. You're supposed to know the math first, then apply it.

I don't know if the backwards approach is a bug or a feature. What I know is that it produces different questions. When you're not trained in a field's vocabulary, you sometimes can't see its assumptions. You end up building things that practitioners say shouldn't work, that turn out to work, and the explanation for why they work is something the practitioners already knew but from a different angle.

---

## What the location means practically

It means I work alone, mostly. The network effects that make research easier in a city — people to ask, hallways to talk in, colleagues who catch your mistakes before they become public mistakes — those don't exist on the Peninsula in this form.

It means I have to be more careful about being wrong. There's no one to catch it in conversation. The mistake goes all the way to the commit or the published post before anyone pushes back.

It also means I'm building for use cases that the standard ML research agenda doesn't prioritize: small compute budgets, no GPU fleet, edge cases that matter to people who are not at the center of the industry's attention. The SCBE pipeline runs in under 8ms on commodity hardware deliberately, not incidentally. If you're building AI governance infrastructure for a system running on a single server in a town with limited cloud connectivity, you can't afford 500ms inference latency per request.

---

## The SAM.gov registration

UEI J4NXHM6N5F59. CAGE 1EXD5. Minority-owned sole proprietorship, active since April 2026.

I registered because PNNL is 25 minutes away and DARPA has programs (DICE, MATHBAC) that are explicitly looking for approaches to AI safety that come from outside the standard academic pipeline. The geometry here is different from what you get from a research group at a coastal university, and there's value in that difference.

I submitted an abstract to MATHBAC in April 2026. Full proposal due June 2026. The work is already in production — the submission is documentation, not speculation.

---

## What I'm actually building

An AI governance framework that runs as deterministic geometry, produces cryptographically signed audit receipts, integrates with existing agent pipelines without requiring a model call, and costs less than $50/month to operate for most use cases.

Six fictional languages from a D&D campaign became a coordinate system. A tabletop magic system became a token tokenizer. 528 pages of session logs became training data for a security layer.

The Wendy's has good wifi. The Olympic Mountains are out the window.

---

*[SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE) is open source. MIT OR Apache-2.0.*
