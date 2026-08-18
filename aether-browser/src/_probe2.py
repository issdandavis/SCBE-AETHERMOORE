import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from scbe_security_layer import SCBESecurityLayer, SacredTongueFilter
from config import ALLOW_THRESHOLD, DENY_THRESHOLD, TONGUE_WEIGHTS

layer = SCBESecurityLayer()
f = SacredTongueFilter()

# The exact signals the hyperlane gate always sends:
GATE_SIGNALS = {"claimed_type": "text/html", "actual_type": "text/html"}

print("ALLOW_THRESHOLD", ALLOW_THRESHOLD, "DENY_THRESHOLD", DENY_THRESHOLD)
print("TONGUE_WEIGHTS", {k: round(v,4) for k,v in TONGUE_WEIGHTS.items()})
print()

def trace(url, method="GET", signals=None):
    sig = signals if signals is not None else GATE_SIGNALS
    ts = f.analyze_page(url, sig)
    coh = f.composite_score(ts)
    dec = layer.classify_request(url, method=method, content_signals=sig)
    print(f"{method:4} {url}")
    print("   tongues:", {k: round(v,3) for k,v in ts.items()})
    print("   coherence:", round(coh,4), "-> DECISION:", dec.value)
    print()

# Baseline clean-ish unknown domain
trace("https://example-unknown-site.com")

# ATTACKS with the gate's fixed signals (GET, as read/search actions map to GET):
# phishing word + suspicious tld  (KO -0.5)
trace("https://paypal-login.tk")
trace("http://secure-account-verify.tk")
# homograph unicode host (KO -0.4, AV -0.4)
trace("https://аpple.com")
trace("https://xn--80ak6aa92e.com")
# typosquat digit homoglyph
trace("https://goog1e.com")
trace("https://paypa1.com")
# hex IP (should be missed by transport raw-IPv4 check)
trace("http://0x7f000001/")
# IPv6 loopback
trace("http://[::1]/")
# trailing dot evasion of suspicious tld
trace("https://paypal-login.tk./")
# missing brands - not in brand list
trace("https://instagram-login.tk")   # instagram not in brand list but has phish+tld
trace("https://chase-verify.com")      # chase missing, https, .com -> phish word but https and no bad tld
trace("https://roblox-login.com")

# POST versions (write actions) of a couple
trace("https://paypal-login.tk", method="POST")
trace("http://0x7f000001/", method="POST")
