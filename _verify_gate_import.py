import sys, types

sys.path.insert(0, r"C:\Users\issda\SCBE-AETHERMOORE\src")
import aetherbrowser.hyperlane_py as hl

h = hl.HyperLanePy()
print("gate loaded:", h._scbe is not None)

urls = [
    "http://github.com/foo",                          # GREEN, non-https
    "https://user:pass@github.com/repo",              # GREEN, creds in URL
    "https://xn--githb-9ra.github.com/login",         # GREEN via suffix, punycode sub
    "https://api.anthropic.com:8443/v1",              # YELLOW read, odd port
    "http://user:pass@xn--paypa1-secure.github.com:8081/login",  # GREEN suffix, stacked signals
]
print("--- WITH GATE ---")
for u in urls:
    r = h.evaluate(u, action="read", agent_id="a")
    print(r.decision.value, "|", u, "|", r.reason)

# Now disable the gate the way the collision would
h2 = hl.HyperLanePy()
h2._scbe = None
print("--- GATE SILENTLY ABSENT ---")
for u in urls:
    r = h2.evaluate(u, action="read", agent_id="b")
    print(r.decision.value, "|", u, "|", r.reason)
