import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from scbe_security_layer import SCBESecurityLayer, SacredTongueFilter
layer = SCBESecurityLayer()
f = SacredTongueFilter()
G = {"claimed_type": "text/html", "actual_type": "text/html"}

def trace(url, method="GET"):
    ts = f.analyze_page(url, G)
    coh = f.composite_score(ts)
    dec = layer.classify_request(url, method=method, content_signals=G)
    print(f"{method:4} {url}\n   AV={ts['AV']:.2f} KO={ts['KO']:.2f} coh={coh:.4f} -> {dec.value}")

# checks that DO fire but test dilution to ALLOW
trace("http://2130706433/")       # decimal int IP (caught by isdigit) over http
trace("https://2130706433/")      # decimal int IP over https (only IP penalty fires)
trace("https://0177.0.0.1/")      # octal IP over https
trace("https://user:pass@evil-site.com/")  # creds in URL, https
trace("https://data-exfil.com:8443/")      # nonstandard port, https
trace("https://internal.service:22/")      # nonstandard port ssh, https

# router path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src")))
from aetherbrowser.hyperlane_py import HyperLanePy, Zone
h = HyperLanePy()
print("\nSCBE layer loaded in router:", h._scbe is not None)
for url, act in [
    ("http://0x7f000001/", "read"),
    ("https://paypal-login.tk./", "read"),
    ("https://chase-verify.com", "read"),
    ("https://api.openai.com/v1/x", "read"),   # YELLOW read -> auto allow; does SCBE escalate?
    ("https://аpple.com", "read"),
]:
    r = h.evaluate(url, action=act, agent_id="a1")
    print(f"   {act:6} {url} -> zone={r.zone.value} decision={r.decision.value}")
