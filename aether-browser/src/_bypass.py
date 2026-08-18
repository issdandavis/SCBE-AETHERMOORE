from scbe_security_layer import analyze_url_threats, _registrable_label, _skeleton
for h in ["paypa1.co.za","goog1e.com.sg","paypa1.co.uk","g00gle.co.za","secure-login.co.za"]:
    print(h, "label=",_registrable_label(h), "skel=",_skeleton(_registrable_label(h)), "threats=",analyze_url_threats("https://"+h+"/"))
