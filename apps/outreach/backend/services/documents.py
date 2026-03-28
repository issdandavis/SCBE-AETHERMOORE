"""
Aethermoor Outreach -- Document generation service.
Generates real, useful document templates with placeholders for user-specific details.
"""

from datetime import datetime, timezone
from typing import Dict, Optional


def generate_document(doc_type: str, context: Optional[Dict] = None) -> Dict:
    """
    Generate a document based on type and context.

    Args:
        doc_type: One of business_plan_summary, permit_inquiry_letter,
                  grant_inquiry_email, patent_description, general_inquiry
        context: Optional dict with user-provided context (name, location, intent, etc.)

    Returns:
        dict with title, content, doc_type
    """
    ctx = context or {}
    name = ctx.get("name", "[YOUR NAME]")
    location = ctx.get("location", "Port Angeles")
    intent = ctx.get("intent", "")
    business_name = ctx.get("business_name", "[BUSINESS NAME]")
    business_type = ctx.get("business_type", "[BUSINESS TYPE -- e.g., retail, service, food]")
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")

    generators = {
        "business_plan_summary": _business_plan_summary,
        "permit_inquiry_letter": _permit_inquiry_letter,
        "grant_inquiry_email": _grant_inquiry_email,
        "patent_description": _patent_description,
        "general_inquiry": _general_inquiry,
    }

    generator = generators.get(doc_type, _general_inquiry)
    return generator(name=name, location=location, intent=intent,
                     business_name=business_name, business_type=business_type, today=today)


def _business_plan_summary(name, location, intent, business_name, business_type, today, **kw) -> Dict:
    content = f"""BUSINESS CONCEPT SUMMARY
Prepared by: {name}
Date: {today}
Location: {location}, WA

---

1. BUSINESS OVERVIEW

Business Name: {business_name}
Business Type: {business_type}
Owner/Founder: {name}
Proposed Location: {location}, WA

Mission Statement:
[Write 1-2 sentences describing your business purpose and what value it provides to the community.]

2. PRODUCTS / SERVICES

Primary offerings:
- [Product/Service 1]: [Brief description and price point]
- [Product/Service 2]: [Brief description and price point]
- [Product/Service 3]: [Brief description and price point]

3. TARGET MARKET

Who are your customers?
- Primary: [e.g., Local residents, tourists, other businesses]
- Secondary: [e.g., Online customers, regional buyers]
- Market size estimate: [e.g., Port Angeles population ~20,000 + 3M annual Olympic NP visitors]

4. COMPETITIVE ADVANTAGE

What makes your business different?
- [Advantage 1: e.g., Only provider of X in Clallam County]
- [Advantage 2: e.g., Lower price point than competitors in Sequim/Seattle]
- [Advantage 3: e.g., Unique combination of services]

5. STARTUP COSTS ESTIMATE

| Item                    | Estimated Cost |
|------------------------|----------------|
| Business registration  | $180 (LLC)     |
| Business license       | $50-100/yr     |
| Equipment/inventory    | $[AMOUNT]      |
| First month rent       | $[AMOUNT]      |
| Insurance              | $[AMOUNT]      |
| Marketing/signage      | $[AMOUNT]      |
| Working capital (3 mo) | $[AMOUNT]      |
| TOTAL                  | $[TOTAL]       |

6. REVENUE PROJECTIONS (YEAR 1)

Monthly revenue target: $[AMOUNT]
Monthly expenses: $[AMOUNT]
Break-even timeline: [X months]

7. NEXT STEPS

[ ] Register with WA Secretary of State
[ ] Apply for City of Port Angeles business license
[ ] Meet with Peninsula SBDC advisor (free)
[ ] Open business bank account
[ ] Get EIN from IRS

---
This summary was prepared with assistance from Aethermoor Outreach.
This is an assistive tool -- not official government or legal advice.
"""
    return {
        "title": f"Business Concept Summary -- {business_name}",
        "content": content,
        "doc_type": "business_plan_summary",
    }


def _permit_inquiry_letter(name, location, intent, business_name, business_type, today, **kw) -> Dict:
    content = f"""{name}
[YOUR ADDRESS]
{location}, WA [ZIP]
[YOUR PHONE]
[YOUR EMAIL]

{today}

City of Port Angeles
Planning and Community Development Department
321 East Fifth Street
Port Angeles, WA 98362

RE: Permit Pre-Application Inquiry

Dear Planning Department,

I am writing to inquire about the permit requirements for a project at [PROPERTY ADDRESS] in {location}.

PROJECT DESCRIPTION:
[Describe your proposed project in 2-3 sentences. Include:
- Type of work (new construction, remodel, change of use, etc.)
- Property address and parcel number if known
- Approximate scope (square footage, number of units, etc.)]

SPECIFIC QUESTIONS:
1. What type of permit(s) will I need for this project?
2. Is the proposed use compatible with the current zoning for this property?
3. What documents do I need to submit with my application?
4. What is the estimated review timeline?
5. Are there any special requirements or overlays that apply to this location?

I would appreciate the opportunity to schedule a pre-application conference to discuss this project before formal submission. I understand pre-application conferences are available at no cost.

I can be reached at [YOUR PHONE] or [YOUR EMAIL]. Thank you for your assistance.

Respectfully,

{name}

---
This letter was prepared with assistance from Aethermoor Outreach.
This is an assistive tool -- not official government or legal advice.
"""
    return {
        "title": f"Permit Inquiry Letter -- {location}",
        "content": content,
        "doc_type": "permit_inquiry_letter",
    }


def _grant_inquiry_email(name, location, intent, business_name, business_type, today, **kw) -> Dict:
    content = f"""Subject: Grant/Funding Inquiry -- {business_type} in {location}

Dear [CONTACT NAME or Economic Development Team],

My name is {name}, and I am [starting/expanding] a {business_type} business in {location}, WA.

I am reaching out to learn about available funding programs, grants, or low-interest loans that may apply to my project.

ABOUT MY PROJECT:
- Business: {business_name}
- Type: {business_type}
- Location: {location}, WA (Clallam County)
- Stage: [Startup / Early stage / Expanding]
- Funding needed: $[AMOUNT] for [equipment, inventory, lease, renovation, etc.]
- Jobs to be created: [NUMBER]

WHAT I HAVE ALREADY:
- [e.g., Business plan completed]
- [e.g., Location identified]
- [e.g., Own equipment valued at $X]
- [e.g., Personal investment of $X]

I am particularly interested in:
- [ ] Revolving loan funds (NODC/NICE programs)
- [ ] WA Commerce Community Development grants
- [ ] SBA microloan or 7(a) programs
- [ ] USDA Rural Development grants
- [ ] Other programs I may not be aware of

Could we schedule a time to discuss which programs might be a good fit? I am available [DAYS/TIMES].

Thank you for your time and support of small business in the North Olympic Peninsula.

Best regards,
{name}
[YOUR PHONE]
[YOUR EMAIL]

---
This email was prepared with assistance from Aethermoor Outreach.
This is an assistive tool -- not official government or legal advice.
"""
    return {
        "title": f"Grant Inquiry Email -- {business_name}",
        "content": content,
        "doc_type": "grant_inquiry_email",
    }


def _patent_description(name, location, intent, business_name, business_type, today, **kw) -> Dict:
    content = f"""INVENTION DISCLOSURE DOCUMENT
Inventor: {name}
Date: {today}
Location: {location}, WA

---

1. TITLE OF INVENTION

[A clear, descriptive title -- e.g., "Self-Adjusting Widget for Improved Widget Performance"]

2. FIELD OF INVENTION

This invention relates to [general field -- e.g., consumer electronics, medical devices,
software, mechanical tools, agricultural equipment].

3. BACKGROUND / PROBLEM STATEMENT

[Describe the problem your invention solves. What currently exists? Why is it inadequate?
2-3 paragraphs.]

Prior approaches include:
- [Existing solution 1 and its limitations]
- [Existing solution 2 and its limitations]

4. SUMMARY OF INVENTION

[1-2 paragraphs describing what your invention IS and what it DOES.
Focus on the novel aspects.]

5. DETAILED DESCRIPTION

[Thorough technical description. Include:
- How it works (step by step if a process, component by component if a device)
- Materials used
- Dimensions or specifications if relevant
- Any alternative embodiments (other ways it could be made)]

6. DRAWINGS / FIGURES

[Reference any attached sketches. Label each figure:]
- Figure 1: [Description]
- Figure 2: [Description]
- Figure 3: [Description]

7. CLAIMS (PRELIMINARY)

What I claim as my invention:

1. A [device/method/system] for [purpose], comprising:
   a. [First element]
   b. [Second element]
   c. [Third element]
   wherein [key distinguishing feature].

2. The [device/method/system] of claim 1, further comprising [additional feature].

3. The [device/method/system] of claim 1, wherein [specific limitation or variation].

8. PRIOR ART SEARCH NOTES

[List any patents, products, or publications you found during your search:]
- US Patent No. [NUMBER]: [Title] -- [How yours differs]
- [Product name]: [How yours differs]

9. INVENTOR DECLARATION

I, {name}, declare that I am the original inventor of the subject matter described above.

Signed: _________________________
Date: {today}

Witnessed by: _________________________
Date: _________________________

---
IMPORTANT: This document is a working template, NOT a filed patent application.
Consider filing a provisional patent application with the USPTO ($160 micro entity fee).
Consult a patent attorney for claims drafting and prosecution.

Prepared with assistance from Aethermoor Outreach.
This is an assistive tool -- not official legal advice.
"""
    return {
        "title": f"Invention Disclosure -- {name}",
        "content": content,
        "doc_type": "patent_description",
    }


def _general_inquiry(name, location, intent, business_name, business_type, today, **kw) -> Dict:
    content = f"""Subject: General Inquiry -- {location}

Dear [DEPARTMENT or CONTACT NAME],

My name is {name}, and I am a resident of {location}, WA.

I am writing to inquire about the following:

{intent if intent else "[Describe your question or request here]"}

Specifically, I would like to know:
1. [Your first question]
2. [Your second question]
3. [Any additional questions]

If this inquiry should be directed to a different department, I would appreciate being pointed in the right direction.

I can be reached at [YOUR PHONE] or [YOUR EMAIL].

Thank you for your assistance.

Sincerely,
{name}

---
This message was prepared with assistance from Aethermoor Outreach.
This is an assistive tool -- not official government or legal advice.
"""
    return {
        "title": f"General Inquiry -- {name}",
        "content": content,
        "doc_type": "general_inquiry",
    }


def get_available_doc_types() -> list:
    """Return all available document types."""
    return [
        {"type": "business_plan_summary", "label": "Business Plan Summary", "for_intent": "start_business"},
        {"type": "permit_inquiry_letter", "label": "Permit Inquiry Letter", "for_intent": "permit_inquiry"},
        {"type": "grant_inquiry_email", "label": "Grant Inquiry Email", "for_intent": "grant_discovery"},
        {"type": "patent_description", "label": "Invention Disclosure", "for_intent": "patent_filing"},
        {"type": "general_inquiry", "label": "General Inquiry Email", "for_intent": "general_inquiry"},
    ]
