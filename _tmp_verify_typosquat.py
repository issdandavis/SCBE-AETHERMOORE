import sys

sys.path.insert(0, r"C:\Users\issda\SCBE-AETHERMOORE\aether-browser\src")
from urllib.parse import urlparse

from scbe_security_layer import SCBESecurityLayer, SacredTongueFilter

layer = SCBESecurityLayer()
signals = {"claimed_type": "text/html", "actual_type": "text/html"}
urls = [
    "https://amazone.de/",
    "https://youtuber.com/",
    "https://apples.com/",
    "https://www.googles.com/",
    "https://amazon.com/",  # control: exact brand
    "https://wikipedia.org/",  # control: unrelated benign
]
f = SacredTongueFilter()
for u in urls:
    scores = f.analyze_page(u, signals)
    coh = f.composite_score(scores)
    dec = layer.classify_request(u, method="GET", content_signals=signals)
    dom = urlparse(u).hostname.lower()
    trust = layer.compute_trust_score(dom)
    risk = (1.0 - trust) * 0.7
    risk = risk * 0.6 + (1.0 - coh) * 0.4
    print(f"{u:32s} KO={scores['KO']:.3f} coherence={coh:.4f} risk={risk:.4f} -> {dec.value}")

# Counterfactual: same pipeline but with KO forced to 1.0 (no typosquat penalty)
print()
for u in ["https://amazone.de/", "https://youtuber.com/"]:
    scores = f.analyze_page(u, signals)
    scores["KO"] = 1.0
    coh = f.composite_score(scores)
    dom = urlparse(u).hostname.lower()
    trust = layer.compute_trust_score(dom)
    risk = (1.0 - trust) * 0.7
    risk = risk * 0.6 + (1.0 - coh) * 0.4
    verdict = "ALLOW" if risk < 0.3 else ("QUARANTINE" if risk < 0.7 else "DENY")
    print(f"counterfactual KO=1.0 {u:28s} coherence={coh:.4f} risk={risk:.4f} -> {verdict}")
