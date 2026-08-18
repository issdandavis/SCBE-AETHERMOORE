# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"C:\Users\issda\SCBE-AETHERMOORE\aether-browser\src")
from urllib.parse import urlparse
from scbe_security_layer import SCBESecurityLayer, SacredTongueFilter

layer = SCBESecurityLayer()
f = SacredTongueFilter()
sig = {"claimed_type": "text/html", "actual_type": "text/html"}

# Build IDN URLs via escapes so no shell encoding can corrupt them
buecher = "https://bücher.de/"            # bücher.de
nihongo = "https://日本語.jp/"     # 日本語.jp
kremlin = "https://президент.рф/"  # президент.рф
puny = "https://xn--bcher-kva.de/"
ascii1 = "https://stackoverflow.com/"
ascii2 = "https://wikipedia.org/"

urls = [buecher, nihongo, kremlin, puny, ascii1, ascii2]
for u in urls:
    host = (urlparse(u).hostname or "").lower()
    nonascii = any(ord(c) > 127 for c in host)
    scores = f.analyze_page(u, sig)
    coh = f.composite_score(scores)
    dec = layer.classify_request(u, method="GET", content_signals=sig)
    trust = layer.compute_trust_score(host)
    base = (1.0 - trust) * 0.7
    risk = base * 0.6 + (1.0 - coh) * 0.4
    print("host=%r nonascii=%s KO=%.2f AV=%.2f coh=%.4f risk=%.4f -> %s"
          % (host, nonascii, scores["KO"], scores["AV"], coh, risk, dec.value))

sys.path.insert(0, r"C:\Users\issda\SCBE-AETHERMOORE\src")
from aetherbrowser.hyperlane_py import HyperLanePy
hl = HyperLanePy()
print("scbe loaded in hyperlane:", hl._scbe is not None)
for u in [buecher, puny, ascii1]:
    r = hl.evaluate(u, action="read", agent_id="t")
    print("hyperlane host=%r zone=%s -> %s | %s"
          % ((urlparse(u).hostname or ""), r.zone.value, r.decision.value, r.reason))
