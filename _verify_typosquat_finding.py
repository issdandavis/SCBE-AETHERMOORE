import sys
from urllib.parse import urlparse

sys.path.insert(0, r"C:\Users\issda\SCBE-AETHERMOORE\aether-browser\src")
from scbe_security_layer import SCBESecurityLayer, SacredTongueFilter

layer = SCBESecurityLayer()
sig = {"claimed_type": "text/html", "actual_type": "text/html"}
f = SacredTongueFilter()
urls = [
    "https://amazone.de/",
    "https://youtuber.com/",
    "https://apples.com/",
    "https://www.googles.com/",
    "https://amazon.de/",
    "https://example.org/",
]
for u in urls:
    ts = f.analyze_page(u, sig)
    coh = f.composite_score(ts)
    dec = layer.classify_request(u, method="GET", content_signals=sig)
    host = (urlparse(u).hostname or "").lower()
    trust = layer.compute_trust_score(host)
    risk = (1.0 - trust) * 0.7
    risk = risk * 0.6 + (1.0 - coh) * 0.4
    print(f"{u:32s} KO={ts['KO']:.3f} AV={ts['AV']:.3f} coh={coh:.4f} risk={risk:.4f} -> {dec}")

# Also verify through the hyperlane router wiring
sys.path.insert(0, r"C:\Users\issda\SCBE-AETHERMOORE\src")
from aetherbrowser.hyperlane_py import HyperLanePy

hl = HyperLanePy()
print("scbe layer loaded in hyperlane:", hl._scbe is not None)
for u in ["https://amazone.de/", "https://github.com/"]:
    r = hl.evaluate(u, action="read", agent_id="verify")
    print(f"{u:32s} hyperlane -> {r.decision.value} zone={r.zone.value} reason={r.reason}")
