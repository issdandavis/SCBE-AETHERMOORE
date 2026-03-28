# Aethermoor Outreach V2 Spec — Full Collaboration Platform

**Author**: Issac Daniel Davis
**Date**: 2026-03-28
**Status**: Spec (V1 MVP building, V2 features planned)

---

## Core Upgrade: From "Here's Who Can" to "Let's Do It Together"

V1: System generates docs, routes to agencies, tracks cases.
V2: System becomes the WAR ROOM where user + professionals + agencies collaborate in real-time.

---

## Feature 1: Video Conference Bridge

### What It Does
When the system detects a question needs professional advice (legal, tax, surveyor, etc.), it doesn't just give a phone number. It offers to SET UP the meeting.

### Flow
1. User asks: "Should I form an LLC or sole prop?"
2. System tags: `NEEDS:ATTORNEY` — this requires legal judgment
3. System says: "I can show you the filing differences, but the right structure for YOUR situation needs an attorney. Want me to schedule a video call with a WA business attorney?"
4. User clicks "Schedule"
5. System:
   - Finds available attorney from partner network
   - Pre-fills a case brief with everything the user already told the system
   - Generates a 1-page summary: intent, location, business type, relevant statutes
   - Sends calendar invite to both parties
   - Opens video room at meeting time

### The Attorney Gets
- Pre-organized case brief (saves them 15 min of intake questions)
- All relevant forms already identified
- User's documents organized and accessible in shared workspace

### The User Gets
- Face-to-face with a real professional
- No phone tag, no office hours friction
- All their documents visible on screen during the call

### Tech
- WebRTC for video (or embed Jitsi Meet — open source, self-hostable, no Zoom license needed)
- Calendar integration (Google Calendar API or Cal.com — open source scheduling)
- Pre-call brief auto-generated from case data

### Revenue
- Free: 1 consultation/month
- Paid tier: unlimited scheduling + priority matching
- Partner revenue: attorneys/CPAs pay to be in the network (lead gen for them)

---

## Feature 2: Diagram Maker

### What It Does
Visual diagrams that map the user's situation — business structure, permit flow, org chart, timeline.

### Diagram Types

**Business Structure Diagram**
```
[You (Issac Davis)]
       |
  [AetherMoore Games LLC]
       |
  +----+----+----+
  |    |    |    |
 SCBE  Outreach  Novel  Shopify
```

**Permit Flow Diagram**
```
[Intent: Build ADU]
    -> [Check Zoning (R1?)]
        -> YES: [Submit Pre-App]
            -> [Site Plan Required?]
                -> YES: [Hire Surveyor]
                    -> [Submit Full App]
                        -> [Review (4-6 weeks)]
                            -> [APPROVED / DENIED / REVISIONS]
```

**Timeline Diagram**
```
Week 1: File LLC ($180)
Week 2: Get EIN (instant) + Business License ($75)
Week 3: SBDC consultation (free)
Week 4: Open bank account
Week 5: Begin operations
```

**Agency Relationship Map**
```
        [Federal]
       /    |    \
    USPTO  IRS   SBA
      |           |
    [State]     [State]
      |           |
    SOS-WA    Commerce
      |
    [Local]
    /    \
  City   Port
  of PA  of PA
```

### Tech
- Mermaid.js (renders diagrams from text — no canvas drawing needed)
- Auto-generated from workflow data
- Exportable as PNG/SVG/PDF
- Editable by user (drag nodes, add steps)

---

## Feature 3: Document Planner & Organizer

### What It Does
For every process, the system knows EXACTLY what documents are needed, in what order, in what format. It creates a bundle — the "Juice Concentrate."

### The Bundle Concept

When a user says "I want to start a business in Port Angeles," the system generates a COMPLETE pre-filled bundle:

```
/bundles/start-business-port-angeles/
  01_CHECKLIST.md                    -- Every step, in order, with checkboxes
  02_WA_LLC_ARTICLES.pdf             -- Pre-filled Articles of Incorporation
  03_EIN_APPLICATION_SS4.pdf         -- Pre-filled IRS Form SS-4
  04_PA_BUSINESS_LICENSE_APP.pdf     -- Pre-filled city application
  05_SBDC_INTAKE_FORM.pdf            -- Pre-filled SBDC consultation request
  06_BUSINESS_PLAN_1PAGE.pdf         -- Generated 1-page business summary
  07_BANK_REQUIREMENTS.md            -- What you need to open a business account
  08_TIMELINE.svg                    -- Visual timeline diagram
  09_AGENCY_MAP.svg                  -- Who to contact and when
  10_OUTREACH_EMAILS/
      - sbdc_intro.txt               -- Draft email to SBDC
      - city_permit_inquiry.txt      -- Draft email to city planning
      - port_inquiry.txt             -- Draft email to Port of PA
  CASE_BRIEF.pdf                     -- Full summary for attorney consultation
  README.md                          -- "Open this first"
```

### Template Library

Official templates pulled from actual agency sources:

| Template | Source | Format |
|----------|--------|--------|
| WA LLC Articles of Organization | sos.wa.gov | PDF fillable |
| IRS Form SS-4 (EIN) | irs.gov | PDF fillable |
| City of PA Business License | cityofpa.us | PDF |
| SBA Business Plan Template | sba.gov | DOCX |
| USPTO Provisional Patent Cover | uspto.gov | PDF fillable |
| WA Master Business Application | dor.wa.gov | Online (link + instructions) |

### Auto-Fill Logic
System takes user's answers from intake and pre-fills every form:
- Legal name -> all forms
- Address -> all forms
- Business type -> articles, license app
- EIN -> everything after IRS step
- Description -> business plan, SBDC intake

### Document Status Tracking
Each document in the bundle has a status:
- TEMPLATE: Blank official form
- DRAFT: Pre-filled, needs review
- READY: User reviewed and approved
- SUBMITTED: Sent to agency
- ACCEPTED: Agency confirmed receipt
- NEEDS_REVISION: Agency requested changes

---

## Feature 4: Source Tagging (Legal Compliance Layer)

Every piece of information the system outputs is tagged:

| Tag | Meaning | Visual |
|-----|---------|--------|
| `SOURCE:OFFICIAL` | From agency website/document | Blue badge + link |
| `SOURCE:STATUTE` | Citing law/regulation | Purple badge + RCW/USC link |
| `SOURCE:PROCEDURE` | Published process steps | Green badge + source link |
| `SOURCE:GENERAL` | Common knowledge / public info | Gray badge |
| `NEEDS:ATTORNEY` | Legal judgment required | Red badge + schedule button |
| `NEEDS:CPA` | Tax judgment required | Orange badge + schedule button |
| `NEEDS:SURVEYOR` | Site-specific expertise | Yellow badge + schedule button |

### How It Works in Practice

User asks: "Do I need a permit to build a shed?"

System responds:
> According to the City of Port Angeles Municipal Code [SOURCE:STATUTE, PAMC 17.xxx],
> structures under 200 sq ft typically don't require a building permit in residential zones.
> However, setback requirements and your specific zoning designation may affect this.
> [NEEDS:ATTORNEY or City Planning confirmation]
>
> Want me to draft an inquiry to City Planning? Or schedule a call?

Every claim has a source. Every judgment call routes to a professional.

---

## Feature 5: Process Bundles ("Juice Concentrate")

### Pre-Built Bundles for Common Workflows

The system ships with ready-to-go bundles for the most common processes:

**Start a Business in Port Angeles**
- 10 documents, all pre-fillable
- 6 agency contacts with hours
- 5-week timeline
- 3 draft outreach emails
- Cost estimate: $255-$455 total

**Get a Building Permit in Port Angeles**
- Permit type decision tree
- Site plan requirements checklist
- Fee schedule (from city website)
- Pre-application form
- Timeline: 4-12 weeks depending on type

**File a Provisional Patent**
- Invention description template
- Prior art search guide (with USPTO links)
- Cover sheet (pre-filled)
- Fee: $160 (micro entity)
- Timeline: file now, 12 months to non-provisional

**Apply for Local Grants**
- NICE/NODC program list
- WA Commerce grant calendar
- SBA loan options
- Application templates per program
- Eligibility checklist

**Register for Federal Contracting (SAM.gov)**
- UEI application walkthrough
- NAICS code selector
- All 16 registration sections mapped
- CAGE code explanation
- Timeline: 7-10 business days

---

## Professional Network (V2 Revenue Engine)

### How Professionals Join
1. Attorney/CPA/surveyor signs up as partner
2. Sets availability, specialties, rates
3. Gets pre-organized case briefs from system
4. Earns clients without marketing

### How Users Benefit
1. Click "Schedule consultation"
2. Get matched with relevant professional
3. Professional already has their case brief
4. Video call with shared document workspace
5. Follow-up tasks auto-generated from call notes

### Revenue Model
- Professionals pay $50-100/mo to be listed (lead gen)
- OR: system takes 10-15% referral fee per consultation
- Users pay $0 for first consultation, then subscription tiers

---

## Technical Architecture (V2)

```
[User Browser]
     |
[Aethermoor Outreach App]
     |
+----+----+----+----+----+
|    |    |    |    |    |
Intake  Workflow  Docs  Video  Diagrams
Engine  Compiler Engine Bridge  Maker
     |         |       |      |
  [SQLite/  [Template [Jitsi  [Mermaid.js]
   Postgres] Library]  Meet]
     |
  [Source Tagger]
     |
  +--+--+
  |     |
[Official  [NEEDS:
 Sources]  Professional]
              |
         [Partner Network]
         [Calendar/Scheduling]
```

---

## Build Sequence

| Phase | Features | Timeline |
|-------|----------|----------|
| V1 (NOW) | Intake, workflow, docs, routing, case tracking | This week |
| V1.5 | Source tagging, diagram maker (Mermaid), bundle generator | Next week |
| V2 | Video bridge (Jitsi), professional network, scheduling | Month 2 |
| V3 | Multi-city, partner portal, mobile app | Month 3-4 |

---

## The "Juice Concentrate" Philosophy

Don't make people figure out what they need.
Don't make them hunt for forms.
Don't make them guess the order.
Don't make them write emails from scratch.

Give them EVERYTHING, pre-organized, pre-filled, in the EXACT order the agency expects.

The user's only job is: review, approve, submit.

That's the juice concentrate. All the water squeezed out. Pure procedure.
