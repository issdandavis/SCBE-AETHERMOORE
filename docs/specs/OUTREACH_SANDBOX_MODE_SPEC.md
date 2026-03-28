# Aethermoor Outreach — Sandbox Mode Spec

**"Practice the process. Crash 100 times. Then file for real."**

---

## Core Concept

For every real government/agency process, we build an exact mock replica:
- Same forms
- Same fields
- Same upload steps
- Same submission flow
- Same review criteria

But it's a sandbox. Nothing gets sent. Nothing costs money. You can fail safely.

---

## How It Works

### 1. Process Replica Engine

For each supported workflow (LLC filing, permit app, patent filing, SAM.gov registration), we build:

```
REAL PROCESS                    SANDBOX REPLICA
-----------                     ---------------
sos.wa.gov LLC form      -->    Mock form (identical fields)
Upload Articles of Org   -->    Mock upload (validates format)
Pay $180                 -->    Mock payment (fake checkout)
Submit                   -->    Mock submit (saves locally)
Wait for response        -->    Mock response (instant, with feedback)
```

The sandbox looks and feels like the real thing. Same colors, same layout, same field names, same error messages. But everything stays local.

### 2. Guided Chatbot Overlay

A chat assistant floats on the right side of every sandbox form:

**What it does:**
- "Click the 'Entity Type' dropdown and select 'Limited Liability Company'"
- "This field wants your registered agent's address — that's YOUR address unless you hire a service"
- "Upload your Articles of Organization here — you saved it at Documents/bundles/start-business/02_WA_LLC_ARTICLES.pdf"
- "This field is asking for your NAICS code — we pre-selected 541715 for you in step 3"

**What it knows:**
- Where every form field maps to in the user's bundle
- What the field expects (format, length, required/optional)
- Where the user's pre-filled document lives on their machine
- Common mistakes for each field

### 3. Document Locator

The chatbot doesn't just say "upload your articles." It says:

> "Your Articles of Organization are saved at:
> `bundles/start-business/02_WA_LLC_ARTICLES.pdf`
>
> This is form UBI-01 from the WA Secretary of State.
> Upload number: Document 2 of 4 in this submission.
> Status: DRAFT — you approved it in Step 2.
>
> [Click here to open the file] [Click here to upload]"

Every document has:
- A filename that matches the process step
- A number in the submission sequence
- A status (TEMPLATE / DRAFT / APPROVED / UPLOADED / SUBMITTED)
- A link to where it's saved

### 4. Mock Submission + Format Validation

When the user clicks "Submit" in the sandbox:

**Step 1: Format Check**
The system validates EVERY field against known requirements:

| Check | Example | Pass/Fail |
|-------|---------|-----------|
| Required fields filled | Business name present? | PASS |
| Field format correct | EIN matches XX-XXXXXXX? | PASS |
| Document format valid | PDF, under 10MB? | PASS |
| Document readable | Can extract text from PDF? | PASS |
| Address format | Street, City, State, ZIP? | PASS |
| Phone format | (XXX) XXX-XXXX? | FAIL — missing area code |
| Date format | MM/DD/YYYY? | PASS |
| Signature present | Digital signature field filled? | FAIL — empty |
| Fee correct | $180 for LLC? | PASS |
| Required attachments | All 4 documents uploaded? | FAIL — missing doc 3 |

**Step 2: Completeness Score**
```
SUBMISSION REVIEW
=================
Format:        92% (11/12 fields correct)
Completeness:  83% (5/6 documents attached)
Compliance:    100% (all required sections present)

ISSUES FOUND:
  [!] Phone number missing area code (field: Contact Phone)
  [!] Signature field empty (field: Authorized Signature)
  [!] Missing document: Operating Agreement (upload slot 3)

VERDICT: NEEDS REVISION (fix 3 issues, then re-submit)
```

**Step 3: Mock Response**
After "submission," the system generates a mock agency response:

> **Mock Response from WA Secretary of State**
>
> Status: RECEIVED (processing)
> Estimated review time: 3-5 business days
>
> Note: Your submission would likely be APPROVED based on format review.
> However, the following items may trigger a real rejection:
> - Operating Agreement not required for filing but recommended
> - Consider adding a registered agent service for reliability
>
> **This is a simulation. Nothing has been filed.**

### 5. Diff View: Mock vs Real

Side-by-side comparison:

```
SANDBOX                          REAL PROCESS
-------                          ------------
[x] Fill out form               [ ] Fill out form (same fields)
[x] Upload 4 docs               [ ] Upload 4 docs
[x] Mock payment ($0)           [ ] Real payment ($180)
[x] Mock submit                 [ ] Real submit
[x] Mock review (instant)       [ ] Real review (3-5 days)
[x] Format score: 92%           [ ] Will agency accept? (likely yes)

READY TO GO LIVE? [Switch to Real Mode]
```

### 6. Practice Counter

"You've practiced this submission 3 times. Your format score improved from 67% to 92%. You're ready."

Track:
- Number of practice attempts
- Score improvement over time
- Which fields you keep getting wrong
- Time to complete (getting faster?)

---

## Supported Sandbox Processes (V1)

### 1. WA LLC Formation (sos.wa.gov replica)
- 12 form fields
- 2-4 document uploads
- $180 mock payment
- Mock UBI number generation

### 2. City of PA Business License (cityofpa.us replica)
- 8 form fields
- 1-2 document uploads
- $75-100 mock payment
- Mock license number

### 3. IRS EIN Application (irs.gov replica)
- 15 form fields (SS-4 replica)
- No uploads
- Free (real process is also free)
- Mock EIN generation

### 4. SAM.gov Entity Registration (sam.gov replica)
- 16 sections (from the official GSA checklist)
- Multiple document uploads
- Free (real process is also free)
- Mock UEI and CAGE code generation

### 5. USPTO Provisional Patent (uspto.gov replica)
- Cover sheet fields
- Specification upload
- Drawing upload (optional)
- $160 mock payment (micro entity)
- Mock application number

---

## Format Validation Rules (The Secret Sauce)

This is what makes the sandbox actually useful — not just practice, but REAL validation.

### Field-Level Rules
```python
VALIDATION_RULES = {
    "business_name": {
        "required": True,
        "max_length": 200,
        "forbidden_chars": ["@", "#", "$"],
        "forbidden_words": ["LLC" if state != "WA" else None],  # state-specific
    },
    "ein": {
        "required": False,  # not needed at filing
        "format": r"^\d{2}-\d{7}$",
        "hint": "Format: XX-XXXXXXX (get from irs.gov)",
    },
    "phone": {
        "required": True,
        "format": r"^\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$",
        "hint": "Include area code: (360) 555-1234",
    },
    "address": {
        "required": True,
        "must_include": ["street", "city", "state", "zip"],
        "no_po_box": True,  # physical address required for SAM.gov
    },
}
```

### Document-Level Rules
```python
DOCUMENT_RULES = {
    "articles_of_organization": {
        "format": ["pdf"],
        "max_size_mb": 10,
        "must_contain": ["registered agent", "principal office"],
        "pages_expected": "1-5",
    },
    "site_plan": {
        "format": ["pdf", "dwg", "png"],
        "max_size_mb": 25,
        "must_contain": ["scale", "north arrow", "property lines"],
    },
}
```

### Submission-Level Rules
```python
SUBMISSION_RULES = {
    "wa_llc": {
        "required_docs": ["articles_of_organization"],
        "optional_docs": ["operating_agreement"],
        "required_fields": ["business_name", "registered_agent", "principal_office"],
        "fee": 180.00,
        "expected_turnaround": "3-5 business days",
    },
}
```

---

## The Fear Factor

This feature exists because filing government forms is SCARY:
- "What if I fill it out wrong?"
- "What if I waste $180 on a rejected application?"
- "What if I miss a required document?"
- "What if they reject it and I don't know why?"

The sandbox eliminates ALL of that fear. Practice until you're confident. Get a format score. See exactly what would happen. THEN file for real.

**Nobody else offers this.** Government agencies give you the form and say "good luck." We give you a flight simulator.

---

## Technical Implementation

### Sandbox Mode Toggle
Every workflow has a mode switch:
```
[SANDBOX MODE] ←→ [REAL MODE]
     ↓                  ↓
  Practice           Submit
  Free               Costs money
  Instant review     Real review time
  No consequences    Binding
```

### Storage
- Sandbox submissions stored locally (SQLite)
- Never sent externally
- User can review history of all practice attempts
- Format scores tracked over time

### Process Replica Builder
For each new process, we need:
1. Field map (from the real form)
2. Validation rules (from agency documentation)
3. Document requirements (from instructions)
4. Mock response template (based on common outcomes)
5. Chatbot script (step-by-step guidance)

This is manual work per process, but once built, it serves every user forever.
