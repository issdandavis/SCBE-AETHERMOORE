# SCBE-AETHERMOORE Customer License Agreement

**Version 1.0 — Effective Date: March 7, 2026**

**Licensor**: Issac Daniel Davis ("Licensor", "Author")
**Contact**: issdandavis@gmail.com

---

## NOTICE

SCBE-AETHERMOORE is the product of independent, self-directed research.
The Author does not endorse any third-party framework, standard, policy,
or vendor without thorough independent evaluation. References to external
standards (NIST, FIPS, ISO, etc.) within the software reflect technical
interoperability — not organizational endorsement or affiliation.

---

## 1. Definitions

**"Software"** means the SCBE-AETHERMOORE platform, including but not limited
to the 14-layer harmonic security pipeline, symphonic cipher implementations,
post-quantum cryptographic primitives, governance decision engine, and all
associated documentation, configuration, and tooling distributed under this
Agreement.

**"Open Source Components"** means portions of the Software distributed under
the MIT License (see LICENSE file), which remain freely available under those
terms.

**"Proprietary Components"** means portions of the Software that are NOT
covered by the MIT License, including but not limited to:
- Multi-agent swarm orchestration (`src/fleet/`, `agents/`)
- Flock governance and shepherd protocols
- Enterprise governance decision pipeline
- Training data, fine-tuning datasets, and model weights (`training-data/`)
- Deployment configurations and infrastructure-as-code (`deploy/`)
- Any component explicitly marked as proprietary in its source header

**"Customer"** means any individual, organization, or entity that has
purchased a license to use the Proprietary Components under this Agreement.

**"Authorized Users"** means employees, contractors, or agents of the
Customer who are authorized to access the Software under this Agreement,
not to exceed the number specified in the applicable Order Form.

**"Order Form"** means a purchase order, invoice, or Stripe checkout
confirmation that references this Agreement and specifies the license
tier, Authorized User count, and fees.

---

## 2. License Grant

### 2.1 Open Source Components
Open Source Components remain available under the MIT License. Nothing in
this Agreement restricts rights granted under the MIT License for those
components.

### 2.2 Proprietary Components — Commercial License
Subject to the terms of this Agreement and payment of applicable fees,
Licensor grants Customer a non-exclusive, non-transferable, revocable
license to:

(a) **Use** the Proprietary Components in Customer's internal operations;

(b) **Deploy** the Software in Customer's production environments, limited
    to the number of instances specified in the Order Form;

(c) **Integrate** the Software's APIs and interfaces into Customer's own
    products and services, provided such products do not compete directly
    with the Software;

(d) **Access** updates, patches, and new releases during the active
    subscription period.

### 2.3 Restrictions
Customer shall NOT:

(a) Sublicense, sell, resell, lease, or distribute the Proprietary
    Components to any third party;

(b) Reverse engineer, decompile, or disassemble the Proprietary Components,
    except as permitted by applicable law;

(c) Remove or alter any proprietary notices, labels, or markings;

(d) Use the Software to develop a competing product or service;

(e) Share access credentials with unauthorized users;

(f) Use the Software for any purpose that violates applicable law,
    including but not limited to unauthorized surveillance, discrimination,
    or weapons development.

---

## 3. License Tiers

| Tier | Authorized Users | Deployment Instances | Swarm Agents | Support |
|------|-----------------|---------------------|--------------|---------|
| **Homebrew** | 1 | 1 | Up to 3 | Community |
| **Professional** | Up to 10 | Up to 5 | Up to 12 | Email (48h SLA) |
| **Enterprise** | Unlimited | Unlimited | Unlimited | Dedicated (24h SLA) |

Pricing is as specified on the applicable Order Form or Stripe checkout
page. All fees are in USD unless otherwise stated.

---

## 4. Payment Terms

### 4.1 Fees
Fees are due as specified in the Order Form. Subscriptions renew
automatically unless cancelled at least 30 days before the renewal date.

### 4.2 Payment Processing
Payments are processed through Stripe. By purchasing a license, Customer
agrees to Stripe's Terms of Service in addition to this Agreement.

### 4.3 Refunds
Licensor offers a 14-day money-back guarantee from the date of initial
purchase. Refund requests after this period are at Licensor's discretion.

### 4.4 Late Payment
Fees unpaid for more than 30 days past the due date may result in
suspension of access to Proprietary Components until payment is received.

---

## 5. Intellectual Property

### 5.1 Ownership
Licensor retains all right, title, and interest in and to the Software,
including all intellectual property rights. This Agreement does not convey
any ownership interest to Customer.

### 5.2 Customer Data
Customer retains all right, title, and interest in data processed by or
through the Software. Licensor does not access, collect, or use Customer
data except as necessary to provide support when explicitly requested.

### 5.3 Feedback
If Customer provides suggestions, ideas, or feedback about the Software,
Licensor may use such feedback without restriction or obligation.

---

## 6. Confidentiality

### 6.1 Proprietary Components
The Proprietary Components constitute confidential information of
Licensor. Customer shall protect such information with at least the
same degree of care it uses for its own confidential information,
but not less than reasonable care.

### 6.2 Non-Disclosure
Customer shall not disclose Proprietary Components, their architecture,
algorithms, or implementation details to any third party without prior
written consent from Licensor.

---

## 7. Warranties and Disclaimers

### 7.1 Limited Warranty
Licensor warrants that the Software will perform substantially in
accordance with its documentation for a period of 90 days from the
date of purchase.

### 7.2 Independent Research Disclaimer
The Software incorporates independently researched implementations of
cryptographic, geometric, and AI governance techniques. The Author's
inclusion of any algorithm, standard, or protocol reflects independent
technical evaluation — NOT endorsement of any organization, vendor,
government agency, or policy position.

### 7.3 Compliance Disclaimer
While the Software implements algorithms aligned with published standards
(e.g., FIPS 203/204/205, NIST AI RMF), Licensor makes NO representation
that the Software has been certified, validated, or endorsed by any
standards body, government agency, or certification authority. Customers
are responsible for their own compliance assessments.

### 7.4 General Disclaimer
EXCEPT FOR THE LIMITED WARRANTY IN SECTION 7.1, THE SOFTWARE IS PROVIDED
"AS IS" WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
NOT LIMITED TO WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
PURPOSE, OR NON-INFRINGEMENT.

---

## 8. Limitation of Liability

IN NO EVENT SHALL LICENSOR BE LIABLE FOR ANY INDIRECT, INCIDENTAL,
SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR ANY LOSS OF PROFITS,
DATA, BUSINESS, OR GOODWILL, REGARDLESS OF THE CAUSE OF ACTION OR
THEORY OF LIABILITY.

LICENSOR'S TOTAL AGGREGATE LIABILITY UNDER THIS AGREEMENT SHALL NOT
EXCEED THE AMOUNTS PAID BY CUSTOMER IN THE TWELVE (12) MONTHS
PRECEDING THE CLAIM.

---

## 9. Term and Termination

### 9.1 Term
This Agreement is effective from the date of purchase and continues
for the subscription period specified in the Order Form.

### 9.2 Termination for Breach
Either party may terminate this Agreement if the other party materially
breaches any term and fails to cure such breach within 30 days of
written notice.

### 9.3 Termination for Convenience
Customer may terminate at any time by providing written notice. No
refund is due for the remaining subscription period unless within
the 14-day refund window (Section 4.3).

### 9.4 Effect of Termination
Upon termination, Customer shall:
(a) Cease all use of Proprietary Components;
(b) Delete all copies of Proprietary Components in Customer's possession;
(c) Certify in writing that such deletion has been completed.

Open Source Components may continue to be used under the MIT License.

---

## 10. General Provisions

### 10.1 Governing Law
This Agreement shall be governed by the laws of the State in which
Licensor resides, without regard to conflict of laws principles.

### 10.2 Dispute Resolution
Any dispute arising under this Agreement shall first be subject to
good-faith negotiation for 30 days. If unresolved, disputes shall
be resolved by binding arbitration under the rules of the American
Arbitration Association.

### 10.3 Entire Agreement
This Agreement, together with any Order Form, constitutes the entire
agreement between the parties and supersedes all prior agreements
relating to the subject matter.

### 10.4 Amendments
This Agreement may only be amended by written agreement signed by
both parties, or by Licensor publishing an updated version with
reasonable notice to Customer.

### 10.5 Severability
If any provision is found unenforceable, the remaining provisions
shall continue in full force and effect.

### 10.6 Assignment
Customer may not assign this Agreement without Licensor's prior
written consent. Licensor may assign this Agreement in connection
with a merger, acquisition, or sale of substantially all assets.

---

## 11. Contact

For licensing inquiries, support, or legal questions:

**Issac Daniel Davis**
Email: issdandavis@gmail.com
Repository: https://github.com/issdandavis/SCBE-AETHERMOORE

---

*This document should be reviewed by qualified legal counsel before use.
It is provided as a template and starting point for commercial licensing.*
