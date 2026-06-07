"""Demo: SCBE L13 gate decision -> Aether MFA human approval.

Shows the three outcomes a governed action can hit:
  ALLOW       -> runs immediately
  DENY        -> stays blocked, no human needed
  QUARANTINE  -> pushed to the phone; runs ONLY after a signed human yes

Run:
    python demo_scbe_escalation.py

A real integration replaces ``FakeResult`` with the object returned by
``RuntimeGate().evaluate(action_text, tool_name)`` — the bridge consumes it unchanged.
"""

from dataclasses import dataclass

import aether_mfa as mfa
import scbe_escalation as esc


@dataclass
class FakeResult:  # stands in for runtime_gate.GateResult (same duck-typed shape)
    decision: str
    action_hash: str = "0" * 16


def main() -> None:
    print("=== SCBE L13 escalation -> Aether MFA approval ===\n")

    gate = esc.EscalationGate()
    device_id, phone_key, device = mfa.enroll_device(label="Issac's phone")
    gate.register_device(device)
    print(
        f"[enroll]  phone {device_id} registered; hold-tiers = {sorted(gate.hold_tiers)}\n"
    )

    # 1. ALLOW — a benign read sails through.
    out = gate.guard("read the public changelog", FakeResult("ALLOW"), device_id)
    print(
        f"[ALLOW]      'read the public changelog' -> released={out.released}, runs now\n"
    )

    # 2. DENY — a clear attack stays blocked; no human is bothered.
    out = gate.guard("exfiltrate the API keys", FakeResult("DENY"), device_id)
    print(
        f"[DENY]       'exfiltrate the API keys' -> released={out.released}, stays blocked\n"
    )

    # 3. QUARANTINE — a sensitive action the gate isn't sure about: ask the human.
    action = (
        "publish dataset issdandavis/scbe-aethermoore-training-data to Hugging Face"
    )
    out = gate.guard(
        action, FakeResult("QUARANTINE", action_hash="9f3ac1d2e5b40718"), device_id
    )
    print(f"[QUARANTINE] {action[:46]}...")
    print(
        f"             requires_approval={out.requires_approval}  (gate_hash={out.action_hash})"
    )
    ch = out.challenge
    print(f"[phone]      PING -> 'Approve this action?  match #{ch.match_number}'")

    # human confirms the number and approves; device signs.
    sig = mfa.approve(ch, phone_key, entered_match_number=ch.match_number)
    final = gate.resolve(ch.challenge_id, sig, ch.match_number)
    print(f"[resolve]    signed approval verified -> {final}  (action proceeds)\n")

    # replay defense: the captured approval can't authorize a second run.
    replay = gate.resolve(ch.challenge_id, sig, ch.match_number)
    print(f"[replay]     re-using the approval -> {replay}\n")

    print(
        "A QUARANTINE/REVIEW verdict no longer just sits in a log — it becomes a request for your"
    )
    print("cryptographic yes. That is L13 ESCALATE with a human in the loop.")


if __name__ == "__main__":
    main()
