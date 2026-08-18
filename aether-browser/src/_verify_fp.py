from scbe_security_layer import analyze_url_threats, SCBESecurityLayer, _registrable_label, _skeleton

layer = SCBESecurityLayer()

tests = [
    # Probe 1: phish word substrings on free TLD (legit sites)
    "https://accountant.tk/",
    "https://accountants.tk/services",
    "https://securedrop.tk/",          # SecureDrop-ish legit
    "https://update-notes.ml/changelog",
    "https://designin.tk/",            # contains 'signin' substring
    "https://recovery.tk/meetings",    # contains 'recover'
    "https://mysecurenotes.ml/",       # contains 'secure'
    "https://walletfriendly.tk/",      # contains 'wallet'
    "https://embankings.ga/",          # contains 'banking'
    # Probe 2: digit-skeleton collapse to brand
    "https://app1e.com/",
    "https://app1eton.com/",
    "https://g4ntt.com/",
    "https://st3am.com/",
    "https://5team.com/",
    # Probe 4: multi-part TLD not in _MULTI_SUFFIXES
    "https://paypal.co.za/",
    "https://google.com.sg/",
    "https://apple.co.za/",
    "https://example.com.sg/",
    "https://www.google.co.uk/",
    # Probe 5: legit IP-literal internal services
    "http://127.0.0.1:8000/",
    "http://192.168.1.10/admin",
    "http://[::1]:3000/",
    "http://10.0.0.5:9200/",
]

for u in tests:
    th = analyze_url_threats(u)
    dec = layer.classify_request(u)
    print(f"{u:45s} label={_registrable_label(u.split('//')[1].split('/')[0]):12s} threats={th} => {dec}")
