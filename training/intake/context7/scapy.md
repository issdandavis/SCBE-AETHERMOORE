# Scapy

Scapy is a Python-based interactive packet manipulation library. It can forge, decode, send, and capture network packets across a wide range of protocols. It supports layer composition, sniffing with BPF filters, and custom protocol dissection.

## Import and Basic Usage

```python
from scapy.all import *

# View available layers
ls()

# View fields for a specific layer
ls(IP)
ls(TCP)

# Create a simple IP packet
pkt = IP(dst="192.168.1.1")
pkt.show()

# Send at layer 3 (IP) and receive response
ans, unans = sr(IP(dst="192.168.1.1")/ICMP(), timeout=2)

# Send at layer 2 (Ethernet)
sendp(Ether()/IP(dst="192.168.1.1")/ICMP(), iface="eth0")

# Send without expecting response
send(IP(dst="192.168.1.1")/ICMP())
```

## Layer Composition with / Operator

Scapy uses the `/` operator to stack protocol layers. Each layer encapsulates the next:

```python
from scapy.all import *

# Ethernet / IP / TCP SYN packet
pkt = Ether(dst="ff:ff:ff:ff:ff:ff") / IP(dst="10.0.0.1") / TCP(dport=80, flags="S")

# IP / ICMP echo request
ping = IP(dst="8.8.8.8") / ICMP()

# IP / UDP / DNS query
dns_query = IP(dst="8.8.8.8") / UDP(dport=53) / DNS(rd=1, qd=DNSQR(qname="example.com"))

# IP / TCP / HTTP-like payload
http_pkt = IP(dst="10.0.0.1") / TCP(dport=80, flags="PA") / Raw(load="GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")

# Three-way handshake simulation
syn = IP(dst="10.0.0.1") / TCP(dport=80, flags="S", seq=100)
syn_ack = sr1(syn, timeout=2)  # Send and receive one response
if syn_ack and syn_ack[TCP].flags == "SA":
    ack = IP(dst="10.0.0.1") / TCP(dport=80, flags="A", seq=syn_ack.ack, ack=syn_ack.seq + 1)
    send(ack)

# Access layers
print(pkt[IP].dst)
print(pkt[TCP].dport)
print(pkt.haslayer(TCP))
```

## Sniffing with BPF Filters and sprintf

Capture live traffic with Berkeley Packet Filters:

```python
from scapy.all import *

# Basic sniff with count limit
packets = sniff(count=10)
packets.summary()

# Sniff with BPF filter (only TCP port 80)
packets = sniff(filter="tcp port 80", count=20, timeout=30)

# Sniff specific interface
packets = sniff(iface="eth0", filter="icmp", count=5)

# Sniff with callback function
def packet_handler(pkt):
    if pkt.haslayer(IP):
        print(f"{pkt[IP].src} -> {pkt[IP].dst}")

sniff(filter="tcp", prn=packet_handler, count=10)

# Using sprintf for formatted output
packets = sniff(filter="tcp", count=10)
for pkt in packets:
    print(pkt.sprintf("{IP:%IP.src% -> %IP.dst%}{TCP: %TCP.sport% -> %TCP.dport%}"))

# Sniff DNS queries with sprintf
def dns_monitor(pkt):
    if pkt.haslayer(DNSQR):
        print(pkt.sprintf("DNS Query: {DNSQR:%DNSQR.qname%}"))

sniff(filter="udp port 53", prn=dns_monitor, store=0)

# Sniff HTTP requests
def http_monitor(pkt):
    if pkt.haslayer(Raw):
        payload = pkt[Raw].load.decode(errors="ignore")
        if "GET" in payload or "POST" in payload:
            print(pkt.sprintf("{IP:%IP.src%} ") + payload.split("\r\n")[0])

sniff(filter="tcp port 80", prn=http_monitor, store=0)

# Save captured packets to PCAP
packets = sniff(filter="tcp", count=100, timeout=60)
wrpcap("capture.pcap", packets)

# Read from PCAP file
packets = rdpcap("capture.pcap")
packets.summary()
```

## ARP Monitoring

Monitor ARP traffic to detect spoofing or new devices:

```python
from scapy.all import *

# Passive ARP monitor
def arp_monitor(pkt):
    if pkt.haslayer(ARP):
        if pkt[ARP].op == 1:  # ARP Request (who-has)
            print(f"ARP Request: {pkt[ARP].psrc} asks who has {pkt[ARP].pdst}")
        elif pkt[ARP].op == 2:  # ARP Reply (is-at)
            print(f"ARP Reply: {pkt[ARP].psrc} is at {pkt[ARP].hwsrc}")

sniff(filter="arp", prn=arp_monitor, store=0)

# Detect ARP spoofing by tracking IP-MAC mappings
arp_table = {}

def arp_spoof_detector(pkt):
    if pkt.haslayer(ARP) and pkt[ARP].op == 2:
        ip = pkt[ARP].psrc
        mac = pkt[ARP].hwsrc
        if ip in arp_table and arp_table[ip] != mac:
            print(f"[ALERT] ARP Spoof detected! {ip} changed from {arp_table[ip]} to {mac}")
        arp_table[ip] = mac

sniff(filter="arp", prn=arp_spoof_detector, store=0)
```

## ARP Ping Host Discovery

Discover live hosts on a local network using ARP:

```python
from scapy.all import *

# ARP ping a single host
ans, unans = srp(Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst="192.168.1.1"), timeout=2, verbose=0)
for sent, received in ans:
    print(f"{received.psrc} is at {received.hwsrc}")

# ARP scan entire subnet
ans, unans = srp(
    Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst="192.168.1.0/24"),
    timeout=3,
    verbose=0
)

print("Live hosts:")
for sent, received in ans:
    print(f"  {received.psrc:15s} - {received.hwsrc}")

print(f"\n{len(ans)} hosts found, {len(unans)} unanswered")

# Using arping shortcut
ans, unans = arping("192.168.1.0/24", verbose=0)

# ARP scan with retry
ans, unans = srp(
    Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst="10.0.0.0/24"),
    timeout=2,
    retry=2,
    verbose=0
)

# Export results
for sent, received in ans:
    print(f"{received.psrc},{received.hwsrc}")
```
