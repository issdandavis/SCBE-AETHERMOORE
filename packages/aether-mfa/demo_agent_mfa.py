"""End-to-end demo: an AI agent requests a sensitive action and you approve it from your phone.

Run:
    python demo_agent_mfa.py

This narrates the full Aether MFA push flow, including a phishing attempt that is correctly denied.
"""

import aether_mfa as mfa


def line(msg: str = "") -> None:
    print(msg)


def main() -> None:
    line("=== Aether MFA -- agent action approval demo ===\n")

    # 1. One-time enrollment: your phone generates a keypair; the server stores only the public key.
    verifier = mfa.PushVerifier(ttl_seconds=120)
    device_id, phone_private_key, device = mfa.enroll_device(label="Issac's phone")
    verifier.register_device(device)
    line(f"[enroll]  phone {device_id} registered; server holds ONLY the public key\n")

    # 2. An AI agent wants to do something sensitive. It asks the verifier for a challenge.
    action = (
        "publish dataset issdandavis/scbe-aethermoore-training-data to Hugging Face"
    )
    line(f"[agent]   Polly agent requests: {action!r}")
    challenge = verifier.create_challenge(device_id, action=action)
    line(f"[server]  challenge {challenge.challenge_id[:12]}... pushed to phone")
    line(f"[screen]  the agent surface shows match-number:  {challenge.match_number}")
    line(
        f"[phone]   PING -> 'Approve: {action[:40]}...?  match #{challenge.match_number}'\n"
    )

    # 3a. Phishing attempt: a DIFFERENT push tries to get blind approval with the wrong number.
    line("[attack]  a look-alike push asks you to approve, but its number is '99'")
    try:
        mfa.approve(challenge, phone_private_key, entered_match_number="99")
    except ValueError as exc:
        line(f"[phone]   you compare numbers, they don't match -> {exc}\n")

    # 3b. Real approval: you confirm the number you see on the agent surface and approve.
    signature = mfa.approve(
        challenge, phone_private_key, entered_match_number=challenge.match_number
    )
    verdict = verifier.verify_approval(
        challenge.challenge_id, signature, challenge.match_number
    )
    line(
        f"[server]  verify Ed25519 signature over the bound action -> {verdict.allow} ({verdict.reason})"
    )
    line(
        f"[agent]   {'PROCEEDS' if verdict.allow else 'BLOCKED'}: {verdict.action[:50]}...\n"
    )

    # 4. Replay defense: the same approval cannot be reused.
    replay = verifier.verify_approval(
        challenge.challenge_id, signature, challenge.match_number
    )
    line(
        f"[replay]  attacker re-sends the captured approval -> {replay.allow} ({replay.reason})"
    )

    line(
        "\nThis is L13 ESCALATE made concrete: a governed agent action that needs a human's"
    )
    line(
        "cryptographic yes -- bound to the exact action, single-use, and phishing-resistant."
    )


if __name__ == "__main__":
    main()
