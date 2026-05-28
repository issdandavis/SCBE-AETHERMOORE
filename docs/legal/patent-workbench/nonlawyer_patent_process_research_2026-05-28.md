# Non-Lawyer Patent Process Research -- 2026-05-28

Purpose: map the full patent process and identify who works in this space for a
living without being a lawyer. This is an internal pro se workbench note, not
legal advice.

## Bottom Line

There are three legitimate non-lawyer lanes:

1. **Pro se inventor** -- the inventor files and prosecutes their own
   application.
2. **Registered patent agent** -- a non-attorney who has passed the USPTO
   registration process and may represent others before the USPTO in patent
   matters.
3. **Support specialists** -- searchers, technical specialists, illustrators,
   docketing staff, and paralegal-style filing assistants who support the work
   but should not hold themselves out as representatives unless registered.

The practical model for us is:

> inventor-led prosecution with agent-style discipline: official-source
> procedure, claim support matrices, prior-art logs, drawing control, docket
> checklists, and conservative response drafting.

## What Non-Lawyer Patent Agents Are

A patent agent is not a lawyer. A patent agent is a USPTO-registered patent
practitioner who can practice before the USPTO in patent matters. The key
credential is USPTO registration, not a state bar license.

Patent agents usually do:

- invention disclosure interviews;
- prior-art searching and claim charting;
- drafting specifications, claims, abstracts, and drawings instructions;
- filing through Patent Center;
- preparing Information Disclosure Statements;
- responding to Office Actions;
- interviewing examiners;
- managing continuations, divisionals, and amendments;
- tracking deadlines and fees.

Patent agents generally do not do:

- court litigation;
- general contract/legal advice;
- infringement lawsuits;
- state-law business disputes;
- non-patent legal representation outside their authorized USPTO practice.

For a solo inventor, the important lesson is procedural: patent agents win by
repeatable checklists, not magic.

## Who Else Does Patent Work Without Being Lawyers

| Role | Useful work | Limit |
|---|---|---|
| Patent searcher | Searches patents, applications, papers, product docs, standards, and claim terms | Search results are not legal conclusions |
| Technical specialist | Translates engineering details into invention disclosure, embodiments, alternatives, and test evidence | If not registered, should not represent others before the USPTO |
| Patent illustrator | Produces formal line drawings and figure sheets | Does not decide claim scope |
| Docketing specialist | Tracks deadlines, forms, fees, and response windows | Administrative support, not legal argument |
| Filing assistant | Uploads documents/forms when authorized by the applicant | Must avoid unauthorized representation |
| Pro se assistance staff | USPTO education and process assistance | USPTO says they cannot give legal advice |

## Full Process Map

### 1. Invention Freeze

Output:

- title;
- inventor list;
- problem statement;
- working implementation evidence;
- dates and priority chain;
- figures or screenshots;
- source-code anchors if software.

How professionals do it:

- create an invention disclosure record;
- identify the actual improvement over known systems;
- list fallback embodiments;
- separate must-have elements from optional embodiments.

### 2. Prior-Art Search

Output:

- query log;
- patent/publication list;
- claim charts against close references;
- difference statement.

How professionals do it:

- search by function, not just title words;
- search patent classes, assignees, inventor names, and citations;
- preserve exact queries and dates;
- never write "no prior art exists"; write "no reference found in this search
  teaches the full combination."

### 3. Claim Strategy

Output:

- independent method claim;
- independent system claim;
- independent computer-readable-medium claim;
- dependent claims for fallback features;
- support matrix for every limitation.

How professionals do it:

- put the business/technical core in the independent claims;
- keep dependent claims as fallback ladders;
- avoid limitations that are not actually implemented or enabled;
- avoid magic adjectives like "secure," "unhackable," or "AI-aligned" unless
  tied to a concrete mechanism.

### 4. Specification Draft

Output:

- title;
- cross-reference to provisional;
- background;
- summary;
- drawing descriptions;
- detailed description;
- claims;
- abstract.

How professionals do it:

- write enough embodiments to support the broad claims;
- define terms;
- include alternatives;
- state computer implementation clearly;
- describe data structures, state transitions, thresholds, and outputs.

### 5. Drawings

Output:

- formal figures with reference numerals or clear block diagrams;
- one brief description per figure.

How professionals do it:

- show the claimed system, not just decoration;
- keep figures consistent with claim terms;
- use figures to support fallback dependent claims.

### 6. Filing Package

Output:

- DOCX specification/claims/abstract;
- drawings;
- ADS;
- oath/declaration;
- micro-entity certification if applicable;
- fee payment.

How professionals do it:

- validate DOCX before final submission;
- review the Patent Center preview, not just local Word;
- download filing receipt and acknowledgment immediately;
- docket all future deadlines.

### 7. Examination

Output:

- Office Action review;
- amended claims if needed;
- remarks distinguishing prior art;
- optional examiner interview.

How professionals do it:

- identify whether rejection is 101, 102, 103, or 112;
- amend narrowly enough to overcome the rejection without surrendering the core;
- argue from claim language and spec support;
- do not overstate.

### 8. Allowance, Continuation, or Appeal

Output:

- issue fee decision;
- continuation/CIP decision;
- appeal decision if needed;
- maintenance-fee docket after issuance.

How professionals do it:

- decide whether the allowed claims are commercially useful;
- file continuation before issuance if more claim scope should be pursued;
- keep a prosecution history that does not unnecessarily limit future claims.

## How This Maps To SCBE-2026-0001

| Professional step | Our artifact |
|---|---|
| Invention disclosure | detailed description, code anchors, filing packet |
| Prior-art log | `prior_art_search_log.md` and this workbench folder |
| Claim strategy | 28-claim DOCX, three independent claims |
| Support matrix | `CLAIM_MATH_SUPPORT_MATRIX_2026-05-28.md` |
| Layer review | `layer_connection_prior_art_review_2026-05-28.md` |
| Filing packet | `filing-packet-scbe-2026-0001/01_SUBMIT_THESE_TO_PATENT_CENTER` |
| Remaining manual gate | Patent Center DOCX Validator and ADS fields |

The SCBE-native version of these support functions is defined in
`scbe_patent_support_specialist_roles_2026-05-28.md`.

## Process Rules For Us

1. Every claim limitation gets one of: spec paragraph, figure, code anchor, or
   test evidence.
2. Prior art goes in logs and IDS decisions, not loose marketing language.
3. Benchmarks support prosecution and product truth, but should not be written
   into claims unless the claim actually requires that measured result.
4. If a feature is newer than the provisional, flag it as possible
   non-provisional-date/CIP material rather than pretending it inherits priority.
5. Avoid invention-promotion companies unless they are only doing a clearly
   bounded service; verify credentials first.
6. Prefer official USPTO sources, then statutes/rules/MPEP, then practitioner
   commentary.

## Scam / Low-Value Vendor Filters

Treat these as red flags:

- promises of guaranteed patent issuance or guaranteed licensing revenue;
- vague "invention marketing" packages;
- pressure to buy expensive promotion before claims are filed;
- refusal to identify a USPTO registration number for anyone giving patent
  prosecution advice;
- generic patentability search reports with no claim chart;
- asking for fees through non-USPTO payment channels while pretending to be the
  USPTO.

## Sources Used

- USPTO Pro Se Assistance Program:
  https://www.uspto.gov/patents-getting-started/using-legal-services/pro-se-assistance-program
- USPTO Applying for Patents:
  https://www.uspto.gov/patents/basics/apply
- USPTO Nonprovisional Utility Filing Guide:
  https://www.uspto.gov/patents/basics/apply/utility-patent?MURL=NonProvisionalPatent
- USPTO Inventors Assistance Center:
  https://www.uspto.gov/learning-and-resources/support-centers/inventors-assistance-center-iac
- USPTO Becoming a Patent Practitioner:
  https://www.uspto.gov/learning-and-resources/patent-and-trademark-practitioners/becoming-patent-practitioner
- USPTO Finding a Patent Practitioner:
  https://www.uspto.gov/learning-and-resources/patent-and-trademark-practitioners/finding-patent-practitioner
- USPTO OED practitioner search:
  https://oedci.uspto.gov/OEDCI/?MURL=FindPatentAttorney
- 37 CFR 11.5, practice before the USPTO in patent matters:
  https://www.law.cornell.edu/cfr/text/37/11.5
- MPEP 401, pro se representation and practitioner selection:
  https://www.uspto.gov/web/offices/pac/mpep/documents/0400_401.htm
- USPTO Patent Pro Bono Program:
  https://www.uspto.gov/patents/basics/using-legal-services/pro-bono/patent-pro-bono-program
- USPTO invention promotion complaints:
  https://www.uspto.gov/patents/basics/using-legal-services/scam-prevention/published-complaints/published
- FTC invention marketing scams:
  https://consumer.ftc.gov/articles/invention-marketing-scams
