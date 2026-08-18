import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from urllib.parse import urlparse

def show(t):
    p = urlparse(t)
    h = p.hostname
    print(repr(t))
    print("   hostname=", repr(h))
    print("   has 'xn--':", "xn--" in (h or ""), "| any ord>127:", any(ord(c) > 127 for c in (h or "")))
    print("   username=", p.username, "password=", p.password, "port(raw parse)=", end=" ")
    try:
        print(p.port)
    except Exception as e:
        print("ERR", e)

# (b) punycode/idn both forms
show("https://xn--80ak6aa92e.com")            # apple.com cyrillic, punycode encoded
show("https://аpple.com")                # cyrillic 'a' + pple, raw unicode
show("https://googе.com")                # cyrillic e, raw unicode

# (d) IP encodings that host.replace('.','').isdigit() misses
for t in ["http://0x7f000001", "http://2130706433", "http://[::1]", "http://0177.0.0.1", "http://127.0.0.1"]:
    p = urlparse(t)
    h = (p.hostname or "").lower()
    print(t, "-> host=", repr(h), "| isdigit-after-strip-dots:", h.replace(".", "").isdigit())

# (e) uppercase / trailing dot
for t in ["http://EVIL.TK", "https://Paypal-LOGIN.tk", "http://evil.tk."]:
    p = urlparse(t)
    h = (p.hostname or "")
    print(t, "-> hostname=", repr(h), "lower=", repr(h.lower()))
