# OWASP Top 10 Web Application Security Risks

The OWASP Top 10 is a standard awareness document for developers and web application security. It represents a broad consensus about the most critical security risks to web applications. Globally recognized by developers as the first step towards more secure coding.

## A01:2021 Broken Access Control

Access control enforces policy such that users cannot act outside of their intended permissions. Failures typically lead to unauthorized information disclosure, modification, or destruction of data, or performing a business function outside the user's limits. Common vulnerabilities include violation of the principle of least privilege, bypassing access control checks by modifying the URL, API request, or manipulating internal state. CORS misconfiguration allows API access from unauthorized origins. Force browsing to authenticated pages as unauthenticated user or to privileged pages as standard user.

## A02:2021 Cryptographic Failures

Previously known as Sensitive Data Exposure, this category focuses on failures related to cryptography which often lead to exposure of sensitive data. Notable CWEs include use of hard-coded passwords, broken or risky crypto algorithms, and insufficient entropy. Determine the protection needs of data in transit and at rest. Use strong adaptive and salted hashing functions with work factor for passwords (Argon2, scrypt, bcrypt, PBKDF2). Ensure up-to-date and strong standard algorithms, protocols, and keys. Encrypt all data in transit with TLS, enforce HTTPS with HTTP Strict Transport Security (HSTS).

## A03:2021 Injection

An application is vulnerable to injection when user-supplied data is not validated, filtered, or sanitized. SQL, NoSQL, OS command, ORM, LDAP, and Expression Language injection are common. Use positive server-side input validation. Use LIMIT and other SQL controls to prevent mass disclosure. For residual dynamic queries, escape special characters. Use parameterized interfaces (prepared statements) exclusively.

## A04:2021 Insecure Design

A new category focusing on risks related to design and architectural flaws, calling for more use of threat modeling, secure design patterns, and reference architectures. Insecure design cannot be fixed by perfect implementation — security controls were never created to defend against specific attacks. Establish and use a secure development lifecycle with AppSec professionals. Use threat modeling for critical authentication, access control, business logic, and key flows.

## A05:2021 Security Misconfiguration

The application might be vulnerable if it is missing appropriate security hardening across any part of the application stack, or improperly configured permissions on cloud services. Unnecessary features are enabled or installed (e.g., unnecessary ports, services, pages, accounts, privileges). Default accounts and passwords are still enabled and unchanged. Error handling reveals stack traces or other overly informative error messages.

## A06:2021 Vulnerable and Outdated Components

Components such as libraries, frameworks, and other software modules run with the same privileges as the application. If a vulnerable component is exploited, such an attack can facilitate serious data loss or server takeover. Remove unused dependencies, unnecessary features, components, files, and documentation. Continuously inventory versions of both client-side and server-side components and their dependencies. Only obtain components from official sources over secure links.

## A07:2021 Identification and Authentication Failures

Confirmation of the user's identity, authentication, and session management is critical to protect against authentication-related attacks. Permits automated attacks such as credential stuffing, brute force. Permits default, weak, or well-known passwords. Uses weak or ineffective credential recovery and forgot-password processes. Uses plain text, encrypted, or weakly hashed password data stores. Implement multi-factor authentication (MFA). Do not ship or deploy with default credentials.

## A08:2021 Software and Data Integrity Failures

Software and data integrity failures relate to code and infrastructure that does not protect against integrity violations. An example is where an application relies upon plugins, libraries, or modules from untrusted sources, repositories, and CDNs. An insecure CI/CD pipeline can introduce unauthorized access, malicious code, or system compromise. Use digital signatures or similar mechanisms to verify software or data is from the expected source and has not been altered.

## A09:2021 Security Logging and Monitoring Failures

Without logging and monitoring, breaches cannot be detected. Insufficient logging, detection, monitoring, and active response occurs when auditable events are not logged, warnings and errors generate no or inadequate log messages, logs are not monitored for suspicious activity. Ensure all login, access control, and server-side input validation failures can be logged with sufficient user context. Ensure logs are generated in a format that log management solutions can easily consume.

## A10:2021 Server-Side Request Forgery (SSRF)

SSRF flaws occur whenever a web application fetches a remote resource without validating the user-supplied URL. It allows an attacker to coerce the application to send a crafted request to an unexpected destination. Sanitize and validate all client-supplied input data. Enforce URL schema, port, and destination with a positive allow list. Do not send raw responses to clients. Disable HTTP redirections.
