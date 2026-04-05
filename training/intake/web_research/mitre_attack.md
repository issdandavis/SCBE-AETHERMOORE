# MITRE ATT&CK Framework

MITRE ATT&CK is a globally-accessible knowledge base of adversary tactics and techniques based on real-world observations. The framework serves as a foundation for developing threat models and methodologies across private sector, government, and cybersecurity communities worldwide. It is open and available to any person or organization at no charge.

## Matrix Structures

The framework organizes adversary behavior across three primary domains:

### Enterprise Matrix
Covers tactics and techniques for traditional IT environments including Windows, macOS, Linux, cloud (AWS, Azure, GCP), network infrastructure, containers, and SaaS platforms.

### Mobile Matrix
Addresses tactics specific to Android and iOS mobile platforms, including device access and network-based effects.

### ICS Matrix
Focuses on Industrial Control Systems including PLCs, HMIs, engineering workstations, and SCADA systems.

## 14 Enterprise Tactics

### 1. Reconnaissance (TA0043)
Gathering information to plan future adversary operations. Techniques include active scanning, searching open technical databases, gathering victim identity and network information.

### 2. Resource Development (TA0042)
Establishing resources to support operations. Techniques include acquiring infrastructure, compromising accounts, developing capabilities, obtaining tools.

### 3. Initial Access (TA0001)
Gaining entry to the target network. Techniques include phishing, exploiting public-facing applications, supply chain compromise, valid accounts, trusted relationships.

### 4. Execution (TA0002)
Running adversary-controlled code. Techniques include command and scripting interpreter (PowerShell, Python, bash), exploitation for client execution, scheduled tasks, WMI.

### 5. Persistence (TA0003)
Maintaining foothold across restarts. Techniques include boot/logon autostart execution, scheduled tasks, account manipulation, implant triggers, server software component modification.

### 6. Privilege Escalation (TA0004)
Gaining higher-level permissions. Techniques include exploitation of vulnerabilities, access token manipulation, process injection, valid account abuse.

### 7. Defense Evasion (TA0005)
Avoiding detection. Techniques include obfuscated files, masquerading, indicator removal, process injection, rootkits, virtualization/sandbox evasion.

### 8. Credential Access (TA0006)
Stealing credentials. Techniques include brute force, credential dumping, input capture, network sniffing, steal web session cookies.

### 9. Discovery (TA0007)
Exploring the environment. Techniques include account discovery, file/directory discovery, network service scanning, system information discovery.

### 10. Lateral Movement (TA0008)
Moving through the environment. Techniques include remote services (RDP, SSH, SMB), internal phishing, exploitation of remote services, lateral tool transfer.

### 11. Collection (TA0009)
Gathering target data. Techniques include automated collection, clipboard data, email collection, screen capture, input capture.

### 12. Command and Control (TA0011)
Communicating with compromised systems. Techniques include application layer protocols, encrypted channels, ingress tool transfer, proxy, remote access software.

### 13. Exfiltration (TA0010)
Stealing data. Techniques include exfiltration over C2 channel, alternative protocol, web service, physical medium, automated exfiltration.

### 14. Impact (TA0040)
Manipulating, interrupting, or destroying systems. Techniques include data destruction, defacement, disk wipe, endpoint denial of service, firmware corruption, ransomware.

## Applications

Security teams use ATT&CK for threat modeling and intelligence, detection engineering, red team and adversary emulation, security gap analysis, maturity assessment, and incident response prioritization. The framework enables organizations to map their defensive capabilities against known adversary behaviors and identify coverage gaps.
