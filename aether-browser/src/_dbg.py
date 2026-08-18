from scbe_security_layer import analyze_url_threats, SCBESecurityLayer
from config import CORE_TRUSTED_DOMAINS, WALL_BLOCKED_DOMAINS
layer = SCBESecurityLayer()
for u in ["http://127.0.0.1:8000/","http://10.0.0.5:9200/","http://192.168.1.10/admin"]:
    from urllib.parse import urlparse
    dom = urlparse(u).hostname
    z = layer.trust_manager.get_zone(dom)
    print(u, "host=",dom, "zone=",z, "threats=",analyze_url_threats(u), "=>", layer.classify_request(u))
print("CORE:", CORE_TRUSTED_DOMAINS)
