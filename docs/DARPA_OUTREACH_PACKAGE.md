# DARPA Outreach Package

## Cold Email Templates

### Email 1: To Timothy Chung (Former OFFSET PM, Swarm Expert)

**Subject:** Jam-Resistant Swarm Coordination - No RF Required

---

Dr. Chung,

I followed your work on OFFSET and the progress toward field-deployable swarm capabilities. I've developed something that addresses a gap I noticed: **how swarms coordinate when RF is denied**.

**The Problem:** Current swarm coordination fails under jamming because it relies on explicit communication.

**My Solution:** Drones "feel" each other through hyperbolic geometry. Each unit maintains a position in a Poincaré ball and a cryptographic phase signature. Compromised units are detected mathematically - no communication required.

**Key Results (Simulation):**
- Rogue drone detected and quarantined in 1 timestep
- 6/6 consensus, zero false positives
- Formation maintained with RF disabled

**Live Demo:** [YOUR_DEPLOYED_URL]/v1/demo/rogue-detection

I'm a solo developer with a working prototype (950 tests passing, ready for hardware integration). Happy to discuss if this aligns with any current or future swarm programs.

Best,
Issac Daniel Davis
issdandavis@gmail.com
GitHub: github.com/issdandavis/SCBE-AETHERMOORE

---

### Email 2: To Phillip Smith (Lift Challenge PM, TTO)

**Subject:** Swarm Coordination Layer for Multi-Drone Lift Operations

---

Dr. Smith,

Congratulations on launching the Lift Challenge - heavy-lift drones will need coordination to be useful in contested environments.

I've developed a **jam-resistant coordination layer** that could complement heavy-lift capabilities:

**What It Does:**
- Enables swarms to maintain formation without RF communication
- Detects compromised/spoofed units through mathematical anomaly detection
- Works with GPS denied (uses internal geometry only)

**Why It Matters for Lift:**
When multiple drones coordinate for heavy payload delivery, a single compromised unit could cause mission failure. My system detects that unit before it acts.

**Technical Brief:** [Link to DARPA_SWARM_BRIEF.md on GitHub]
**Live Demo:** [YOUR_DEPLOYED_URL]/v1/demo/swarm-coordination?agents=20

Would welcome 15 minutes to discuss if this could support Lift Challenge participants or future TTO programs.

Best,
Issac Daniel Davis
issdandavis@gmail.com

---

### Email 3: Generic TTO Inquiry

**Subject:** Novel Swarm Coordination Approach - Seeking Right Program Fit

---

To the Tactical Technology Office,

I've developed a swarm coordination system that operates without RF communication - drones detect each other and identify compromised units through hyperbolic geometry.

**Capability Summary:**
- Jam-resistant: Works under full RF denial
- Rogue detection: Mathematical anomaly detection, 0 false positives
- Decentralized: No single point of failure
- Proven: 950 tests passing, simulation-validated

**Potential Applications:**
- Contested ISR swarms
- Counter-UAS (detect adversary drones)
- Resilient logistics/resupply
- Urban operations (no RF signature)

I'm seeking guidance on which program or PM this might align with. Happy to provide a technical deep-dive or live demonstration.

Best,
Issac Daniel Davis
issdandavis@gmail.com
GitHub: github.com/issdandavis/SCBE-AETHERMOORE

---

## Relevant DARPA Programs & Contacts

### Tactical Technology Office (TTO)

| Role | Name | Focus |
|------|------|-------|
| Former OFFSET PM | Timothy Chung | Swarm tactics, 250+ drone coordination |
| Lift Challenge PM | Phillip Smith | Heavy-lift drones, payload delivery |
| TTO Director | (Check darpa.mil) | Overall tactical systems |

**TTO Website:** https://www.darpa.mil/about/offices/tto

### Key Programs (Historical & Current)

| Program | Status | Relevance |
|---------|--------|-----------|
| **OFFSET** | Completed 2021 | Direct swarm precedent |
| **CODE** | Active | Collaborative ops in denied environment |
| **Lift Challenge** | Opens Jan 2026 | Multi-drone coordination |
| **Assured Autonomy** | Active | Provable AI behavior |

---

## SBIR/STTR Opportunities

### How to Find Current Topics

1. Go to: https://www.dodsbirsttr.mil/
2. Click "More Filters"
3. Select "DARPA" as Component
4. Search keywords: "autonomous", "swarm", "unmanned", "coordination"

### Recent Relevant Topics

| Topic | Description | Status |
|-------|-------------|--------|
| **ALIAS Missionized Autonomy** (HR0011SB20254XL-01) | Autonomous MUM-T for emergency services | Pre-release Sept 2025 |
| **ISaAc** (HR0011SB20254-07) | Inertially scaled UAVs | Closed June 2025 |

### SBIR Timeline

- Topics pre-release **first Wednesday of every month**
- Monitor for: "swarm", "contested environment", "autonomous coordination"
- Phase I = $50-250K (feasibility)
- Phase II = $750K-1.5M (prototype)

---

## SAM.gov BAA Search

### How to Search

1. Go to: https://sam.gov/search
2. Select "Contract Opportunities"
3. Filter by Agency: "Defense Advanced Research Projects Agency"
4. Keywords to try:
   - "autonomous systems"
   - "swarm"
   - "unmanned aircraft"
   - "denied environment"
   - "resilient coordination"

---

## Your Pitch Points (Use These)

### The Hook
> "Drones that feel each other through math, not radio waves."

### The Problem
> "Current swarm coordination fails when jammed because it relies on RF communication."

### The Solution
> "Hyperbolic geometry embedding where each drone's position encodes trust. Compromised units are mathematically anomalous - detected without any communication."

### The Proof
> "950 tests passing. Rogue detected at step 0 with 6/6 consensus. Zero false positives. Ready for hardware integration."

### The Ask
> "15 minutes to demonstrate the live system and discuss program fit."

---

## Attachments to Prepare

1. **DARPA_SWARM_BRIEF.md** (already created)
2. **Live demo URL** (deploy first!)
3. **GitHub repo link** (public or invite-only)
4. **One-page capability summary** (PDF version of brief)

---

## Next Steps Checklist

- [ ] Deploy API to public URL (GCP or AWS)
- [ ] Test all three demo endpoints work
- [ ] Find current TTO director name on darpa.mil
- [ ] Send Email 1 to Timothy Chung (LinkedIn or DARPA alumni networks)
- [ ] Send Email 2 to Phillip Smith (via darpa.mil contact)
- [ ] Submit generic inquiry via darpa.mil/work-with-us
- [ ] Set calendar reminder: Check SBIR topics first Wednesday of each month
- [ ] Register for Lift Challenge when it opens (Jan 2026)
