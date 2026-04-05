# OWASP API Security Top 10 (2023)

The OWASP API Security project focuses on strategies and solutions to understand and mitigate the unique vulnerabilities and security risks of APIs. APIs are a critical attack surface as they expose application logic and sensitive data.

## API1:2023 Broken Object Level Authorization (BOLA)

APIs tend to expose endpoints that handle object identifiers, creating a wide attack surface of object-level access control issues. Object level authorization checks should be considered in every function that accesses a data source using an ID from the user. Attackers substitute the ID of their own resource in the API call with an ID of a resource belonging to another user. Prevention: implement proper authorization checks based on user policies and hierarchy. Don't rely on client-sent IDs — use IDs stored in the session.

## API2:2023 Broken Authentication

Authentication mechanisms are often implemented incorrectly, allowing attackers to compromise authentication tokens or exploit implementation flaws to assume other users' identities. Weak passwords, missing MFA, credential stuffing, JWT issues (weak signing, missing expiration, accepting none algorithm). Prevention: use standard authentication mechanisms, implement rate limiting, use strong password policies, implement MFA.

## API3:2023 Broken Object Property Level Authorization

Combining excessive data exposure and mass assignment. APIs expose object properties that users should not be authorized to read (excessive data exposure) or modify (mass assignment). Attackers manipulate object properties they are not supposed to access. Prevention: validate returned data against API schema, implement property-level authorization.

## API4:2023 Unrestricted Resource Consumption

APIs do not limit the size or number of resources requested by the client. This can lead to denial of service (DoS), brute force attacks, and resource exhaustion. Missing rate limiting, execution timeouts, maximum memory allocation, maximum file upload size, excessive operations in single request. Prevention: implement rate limiting, set execution timeouts, limit payload sizes, implement pagination.

## API5:2023 Broken Function Level Authorization

Complex access control policies with different hierarchies, groups, and roles create administrative functions that are accessible by regular users. Attackers send legitimate API calls to endpoints they should not have access to. Prevention: deny all access by default, implement consistent authorization across all endpoints, review function-level permissions.

## API6:2023 Unrestricted Access to Sensitive Business Flows

APIs vulnerable to this risk expose a business flow without compensating for the damage that can be caused by automated, excessive access to the flow. Rate limiting alone is insufficient — the business impact of the flow must be considered. Examples: automated purchasing (ticket scalping), automated account creation (spam), automated data harvesting. Prevention: identify critical business flows, implement device fingerprinting, human detection (CAPTCHA), non-human pattern detection.

## API7:2023 Server Side Request Forgery (SSRF)

SSRF flaws occur when an API fetches a remote resource without validating the user-supplied URI. An attacker can force the application to send crafted requests to unexpected destinations. Can access internal services, cloud metadata endpoints, and internal networks. Prevention: validate and sanitize all client-supplied URLs, use allowlists for remote origins, disable HTTP redirections.

## API8:2023 Security Misconfiguration

APIs and their supporting systems can contain misconfigurations that impact security. Missing security hardening, unnecessary features enabled, missing TLS, CORS misconfigured, verbose error messages, missing security headers. Prevention: implement a hardening process, review and update configurations regularly, automate configuration assessment.

## API9:2023 Improper Inventory Management

APIs tend to expose more endpoints than traditional web applications, making proper documentation and inventory crucial. Outdated documentation, missing asset inventory, exposed debug endpoints, running deprecated API versions, missing authentication on management endpoints. Prevention: inventory all API hosts, document all aspects of the API, generate documentation automatically, apply security controls to all exposed API versions.

## API10:2023 Unsafe Consumption of APIs

Developers tend to trust data received from third-party APIs more than user input. Attackers target integrated services to indirectly compromise the API. Insufficient validation of third-party API responses, following redirects without validation, no resource limits for processing third-party responses. Prevention: validate all data received from integrated APIs, use TLS for all interactions, apply the same input validation to third-party data as to user input.
