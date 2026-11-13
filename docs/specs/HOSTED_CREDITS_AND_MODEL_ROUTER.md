# Hosted credits and model-router contract

Status: design contract. No live billing, credit wallet, hosted router, or paid
API is claimed by the `4.3.4` package candidate.

## Product boundary

- Local scanning, deterministic Clay actions, and local agent routing remain
  free and do not require an account.
- Hosted model calls are opt-in and consume prepaid credits.
- A request never silently changes from local to paid execution.
- “Best model” means the best measured option inside the user's quality,
  privacy, latency, and cost limits—not the most expensive provider.

## Request flow

```text
scoped SCBE API token
  -> policy and privacy gate
  -> deterministic/Clay/local-model attempt when allowed
  -> candidate model estimates (quality, latency, maximum cost)
  -> atomic worst-case credit reservation
  -> one provider call with an idempotency key
  -> verified usage receipt
  -> settle actual cost + disclosed service fee
  -> release unused reservation
  -> user-visible routing and balance receipt
```

If no candidate meets the policy or the wallet cannot reserve the maximum cost,
the request fails before contacting a paid provider.

## API-token contract

- Generate the token once and display it once; store only a salted verifier or
  cryptographic hash.
- Give tokens explicit scopes such as `scan`, `route:local`, `route:hosted`,
  `usage:read`, and `token:rotate`.
- Support expiration, rotation, immediate revocation, per-token rate limits,
  per-request cost caps, and daily/monthly spend caps.
- Never put Stripe, Metronome, or model-provider secrets in a user token.
- Do not log raw tokens, prompts, provider credentials, or full model outputs.

## Payments and credit accounting

Use an isolated Stripe sandbox for development. Prepaid top-ups use
Stripe-hosted Checkout; a success page never grants credits. A server-side
webhook verifies Stripe's signature and idempotently records paid, asynchronous
success, failure, refund, dispute, and fraud-warning transitions before the
credit ledger changes. Production services use restricted Stripe API keys with
least privilege and a secrets vault.

For a new AI usage/credit product, use Metronome Contracts, rate cards, credits,
and commits rather than inventing a second usage-billing engine. Every usage
event needs a stable transaction identifier so retries cannot double-charge.
Stripe remains the payment/invoice provider; Metronome rates usage and tracks
credit burn. Exact API objects and prices require a separate sandbox design and
write approval.

The internal operational ledger remains double-entry even when an external
billing system is authoritative:

| Entry | Debit | Credit |
| --- | --- | --- |
| Paid top-up verified | payment clearing | customer available credits |
| Request reservation | customer available credits | customer reserved credits |
| Provider settlement | customer reserved credits | provider cost payable |
| Service fee | customer reserved credits | service revenue |
| Unused estimate | customer reserved credits | customer available credits |
| Refund/dispute | customer credits or reserve | payment/refund liability |

No balance update is an in-place counter mutation without a corresponding
immutable ledger entry.

## Staying out of the red

1. Reserve the provider's worst-case cost before dispatch.
2. Reject or downgrade requests that exceed the user cap or available balance.
3. Reconcile from provider usage, then refund the estimate delta.
4. Maintain provider-specific circuit breakers for stale pricing, outage,
   abnormal latency, and cost spikes.
5. Keep a platform reserve for refunds, disputes, and rounding; do not count
   unearned prepaid credit as profit.
6. Publish the service fee and routing policy. Never hide margin in token counts
   or substitute a costlier model without consent.
7. Track gross margin by provider/model/route and stop a route automatically if
   measured cost exceeds collected revenue plus its allowed subsidy.

Tax is a launch requirement, not a checkbox. Before charging customers, assess
sales-tax/VAT/GST registrations and configure the applicable tax workflow.
Simply enabling automatic tax without an active registration does not cause tax
to be collected.

## Model-routing policy

Each model lane has a versioned capability card:

- measured task scores and confidence intervals;
- input/output modalities and context limits;
- median/tail latency;
- current input, cached-input, output, and tool-call costs;
- privacy/data-retention class and allowed regions;
- tool/action permissions;
- failure and refusal rates on the relevant task family.

Routing order:

1. deterministic compiler/action primitive;
2. local Clay or another approved local model;
3. inexpensive remote model that clears the task's quality floor;
4. larger specialist model only after uncertainty, verifier disagreement, or
   task risk crosses a declared escalation threshold;
5. human review when no allowed model clears the gate.

Provider marketing scores do not choose a lane. Use rolling task-specific
evaluations, holdouts, and matched cost/quality comparisons. Record the selected
lane and alternatives in the receipt without exposing hidden reasoning.

## Clay's economic role

Clay should first become reliable at bounded actions, compilation, routing, and
verification. Every task completed locally avoids provider spend. Clay can also
draft a plan or action token stream for a remote model to verify, reducing paid
output tokens. It must not receive payment authority or bypass the deterministic
compiler/security gates.

## Privacy and support

- Usage billing receives counts, model/version, route ID, duration, and cost
  dimensions—not raw prompts or outputs.
- Diagnostic upload remains off by default and follows
  `GUIDED_INSTALLER_AND_SUPPORT.md`.
- Customer content and support diagnostics are not training data without a
  separate explicit consent and review pipeline.
- Users can export their balance/usage ledger and see the model, provider cost,
  fee, reservation, refund, and final charge for every hosted request.

## Implementation stages

1. Sandbox-only API-token service and immutable local credit ledger.
2. Stripe Checkout plus signature-verified, idempotent webhook fulfillment.
3. Metronome catalog/contract/credit design and shadow usage ingestion.
4. Local/Clay-first router with synthetic credits and no provider writes.
5. One capped provider lane, prepaid only, with reservation/reconciliation.
6. Multi-provider benchmark router, spend circuit breakers, refunds/disputes,
   tax review, and operator reconciliation.
7. Independent security and accounting audit before general availability.
