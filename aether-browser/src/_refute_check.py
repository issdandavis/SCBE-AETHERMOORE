"""Adversarial reproduction of the 'risk blend caps below DENY_THRESHOLD' finding."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scbe_security_layer import SCBESecurityLayer, SacredTongueFilter
from config import ALLOW_THRESHOLD, DENY_THRESHOLD, METHOD_RISK_WEIGHTS, TONGUE_WEIGHTS

layer = SCBESecurityLayer()
stub = {"claimed_type": "text/html", "actual_type": "text/html"}

url = "http://paypal-verify.tk/"
print("=== concrete case:", url, "===")
dom = "paypal-verify.tk"
zone = layer.trust_manager.get_zone(dom)
trust = layer.compute_trust_score(dom)
print("zone:", zone, " trust:", round(trust, 6), " 1-trust:", round(1 - trust, 6))
ts = layer.tongue_filter.analyze_page(url, stub)
coh = layer.tongue_filter.composite_score(ts)
print("tongue scores:", {k: round(v, 4) for k, v in ts.items()}, " coherence:", round(coh, 6))
for m in ("GET", "POST", "DELETE"):
    base = (1 - trust) * 0.7 + METHOD_RISK_WEIGHTS.get(m, 0.5) * 0.3
    blended = base * 0.6 + (1 - coh) * 0.4
    dec = layer.classify_request(url, method=m, content_signals=stub)
    print(f"{m}: base={base:.4f} blended={blended:.4f} decision={dec}")

# Worst-case bound: coherence floor when KO=0 and AV=0 but stub signals leave RU/CA/UM/DR at defaults
worst = dict(ts)
worst["KO"] = 0.0
worst["AV"] = 0.0
coh_floor = layer.tongue_filter.composite_score(worst)
print("\ncoherence floor with KO=0,AV=0 (stub leaves RU/CA/UM/DR):", round(coh_floor, 6))

# Even theoretical coherence = 0 (all six tongues zero):
for m, w in sorted(METHOD_RISK_WEIGHTS.items(), key=lambda kv: kv[1]):
    base = (1 - trust) * 0.7 + w * 0.3
    max_risk_coh0 = base * 0.6 + 1.0 * 0.4         # absolute ceiling, coherence=0
    max_risk_floor = base * 0.6 + (1 - coh_floor) * 0.4  # realistic ceiling with stub signals
    print(f"{m:8s} w={w}: ceiling(coh=0)={max_risk_coh0:.4f}  ceiling(coh_floor)={max_risk_floor:.4f}  DENY_THRESHOLD={DENY_THRESHOLD}")

# Try to REFUTE: hunt for ANY unknown-domain URL+GET/POST that classify_request DENYs via content path
print("\n=== refutation hunt: worst adversarial URLs (GET + POST) ===")
attack_urls = [
    "http://paypal-verify.tk/",
    "http://user:pass@paypa1-login-verify-secure.tk:8081/",     # creds + typosquat + phish + tld + port
    "http://xn--pypal-4ve.tk/login",                             # punycode
    "http://аpple-secure-login-verify.ru:8081/",           # non-ascii + phish + tld + port
    "http://login:steal@192.168.13.37:31337/verify",            # creds + raw IP + weird port
    "javascript:alert(1)//paypal-login-verify.tk",
    "data:text/html;base64,xxx",
]
hostile = {
    "claimed_type": "text/html", "actual_type": "application/x-msdownload",
    "uses_eval": True, "crypto_mining_detected": True, "fingerprinting_detected": True,
    "third_party_trackers": 50, "cookie_count": 99, "permission_requests": 10,
    "permissions_granted": 0, "malformed_html": True, "mime_mismatch": True,
    "inline_script_count": 99, "uses_wasm": True,
}
any_deny = False
for u in attack_urls:
    for sig in (stub, hostile):
        for m in ("GET", "POST"):
            d = layer.classify_request(u, method=m, content_signals=sig)
            tag = "stub" if sig is stub else "hostile"
            if str(d).endswith("DENY"):
                any_deny = True
            print(f"{m} {tag:7s} {u[:55]:55s} -> {d}")
print("\nANY DENY reached on GET/POST:", any_deny)

# And the hyperlane wiring end-to-end
print("\n=== hyperlane end-to-end ===")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
try:
    from src.aetherbrowser.hyperlane_py import HyperLanePy
    hl = HyperLanePy()
    print("scbe layer loaded in hyperlane:", hl._scbe is not None)
    for u in ("http://paypal-verify.tk/", "https://github.com/", "http://user:pass@paypa1-login.tk:8081/"):
        for act in ("read", "submit"):
            r = hl.evaluate(u, action=act, agent_id="probe")
            print(f"{act:6s} {u[:45]:45s} -> {r.decision} zone={r.zone} reason={r.reason[:80]}")
except Exception as e:
    print("hyperlane import failed:", type(e).__name__, e)
