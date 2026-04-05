# CWE Top 25 Most Dangerous Software Weaknesses (2024)

The CWE Top 25 is a list of the most common and impactful software weaknesses, compiled by MITRE using real-world vulnerability data from the National Vulnerability Database (NVD). These weaknesses lead to serious vulnerabilities in software that can be exploited by adversaries.

## CWE-79: Improper Neutralization of Input During Web Page Generation (Cross-site Scripting / XSS)

The product does not neutralize or incorrectly neutralizes user-controllable input before it is placed in output that is used as a web page served to other users. XSS allows attackers to inject client-side scripts into web pages viewed by other users. Types: Reflected XSS (non-persistent), Stored XSS (persistent), DOM-based XSS. Prevention: encode output, validate input, use Content Security Policy (CSP), use HTTPOnly cookie flag.

## CWE-787: Out-of-bounds Write

The product writes data past the end, or before the beginning, of the intended buffer. Can lead to memory corruption, code execution, or denial of service. Common in C/C++ programs. Prevention: use bounds checking, safe string functions, memory-safe languages.

## CWE-89: Improper Neutralization of Special Elements used in an SQL Command (SQL Injection)

The product constructs SQL commands using externally-influenced input without proper neutralization. Allows attackers to modify the intent of SQL queries, read/modify/delete data, and execute administrative operations. Prevention: use parameterized queries (prepared statements), stored procedures, input validation, least privilege database accounts.

## CWE-352: Cross-Site Request Forgery (CSRF)

The web application does not verify that a request was intentionally sent by the user who submitted it. Allows attackers to trick authenticated users into submitting malicious requests. Prevention: use anti-CSRF tokens, SameSite cookie attribute, verify Origin/Referer headers, require re-authentication for sensitive operations.

## CWE-22: Improper Limitation of a Pathname to a Restricted Directory (Path Traversal)

The product uses external input to construct a pathname intended to identify a file or directory below a restricted parent, but does not properly neutralize special elements (../) that can resolve to a location outside the restricted directory. Prevention: canonicalize paths, use allowlists, chroot jails.

## CWE-125: Out-of-bounds Read

The product reads data past the end, or before the beginning, of the intended buffer. Can expose sensitive information from memory. Common in C/C++ programs. Prevention: bounds checking, safe buffer operations, memory-safe languages.

## CWE-78: Improper Neutralization of Special Elements used in an OS Command (OS Command Injection)

The product constructs OS commands using externally-influenced input without proper neutralization. Allows arbitrary command execution on the host operating system. Prevention: avoid OS commands when possible, use library calls instead, parameterize arguments, input validation.

## CWE-416: Use After Free

The product references memory after it has been freed, which can lead to corruption, crashes, or code execution. Particularly dangerous in C/C++. Prevention: set pointers to NULL after freeing, use smart pointers, use memory-safe languages, ASAN tooling.

## CWE-862: Missing Authorization

The product does not perform an authorization check when an actor attempts to access a resource or perform an action. Allows unauthorized access to protected functionality. Prevention: enforce authorization checks on every request, use centralized authorization framework, default-deny access control.

## CWE-434: Unrestricted Upload of File with Dangerous Type

The product allows file upload without restricting the type of file. Allows uploading of executable code (web shells, malware). Prevention: validate file types (content, not just extension), store uploads outside webroot, use random filenames, scan for malware.

## CWE-94: Improper Control of Generation of Code (Code Injection)

The product constructs code segments using externally-influenced input without proper neutralization. Allows attackers to inject and execute arbitrary code. Prevention: avoid dynamic code generation, use sandboxing, input validation.

## CWE-20: Improper Input Validation

The product receives input but does not validate or incorrectly validates that the input has the properties required to process the data safely. Root cause of many other weaknesses. Prevention: validate all inputs on server-side, use allowlists, reject unexpected input.

## CWE-77: Improper Neutralization of Special Elements used in a Command (Command Injection)

Similar to OS command injection but applies to any command interpreter. Prevention: use APIs instead of shell commands, parameterize inputs, apply input validation.

## CWE-287: Improper Authentication

The product does not properly verify the identity of a user. Allows unauthorized access to protected resources. Prevention: use established authentication frameworks, implement MFA, use secure session management.

## CWE-269: Improper Privilege Management

The product does not properly assign, modify, track, or check privileges for an actor. Allows privilege escalation. Prevention: apply least privilege, separate administrative functions, audit privilege assignments regularly.
