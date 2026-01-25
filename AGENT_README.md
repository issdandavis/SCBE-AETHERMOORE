# SCBE-AETHERMOORE AI Agent

Your AI-powered coding assistant for secure development with SCBE-AETHERMOORE.

## Features

### 🤖 AI Chat Assistant
Ask questions about SCBE, cryptography, security, and coding in natural language.

```bash
agent> ask
You: How does SCBE work?
Agent: SCBE works through a multi-stage process...
```

### 🔍 Secure Web Search
Search the web with SCBE-encrypted queries for privacy.

```bash
agent> search
Search: post-quantum cryptography
🔐 Encrypting query with SCBE...
✓ Found 3 results
```

### 💻 Code Library
Access ready-to-use code examples for Python and TypeScript.

**Python Examples:**
- Encrypt/decrypt messages
- Generate harmonic signatures
- Feistel network operations

**TypeScript Examples:**
- Harmonic scaling
- Post-quantum cryptography
- Quasicrystal lattice

```bash
agent> code
Select language (1-2): 1
# Shows Python examples
```

### 🛡️ Security Scanner
"Antivirus" for your code - scans for security vulnerabilities.

**Detects:**
- Dangerous functions (eval, exec)
- Hardcoded credentials
- SQL injection risks
- Insecure random number generation
- Command injection vulnerabilities
- Missing error handling

```bash
agent> scan
Paste your code (press Ctrl+D when done):
# Paste your code here
🔍 Scanning for vulnerabilities...
✅ NO VULNERABILITIES FOUND!
```

## Installation

```bash
# Make executable (Unix/Linux/Mac)
chmod +x scbe-agent.py

# Run directly
./scbe-agent.py

# Or with Python
python scbe-agent.py
```

## Usage

### Quick Start

```bash
$ python scbe-agent.py

╔═══════════════════════════════════════════════════════════╗
║        SCBE-AETHERMOORE AI AGENT v3.0.0              ║
║     Your AI Coding Assistant for Secure Development       ║
╚═══════════════════════════════════════════════════════════╝

Type 'ask' to chat, 'help' for commands

agent> help
```

### Commands

| Command | Description |
|---------|-------------|
| `ask` | Chat with AI assistant |
| `search` | Secure web search |
| `code` | View code examples |
| `scan` | Security vulnerability scanner |
| `help` | Show help |
| `exit` | Exit agent |

## Examples

### Example 1: Ask About SCBE

```bash
agent> ask
You: What is SCBE?
Agent: SCBE (Spectral Context-Bound Encryption) is a next-generation 
security framework that uses hyperbolic geometry and signal processing...

You: Is it quantum-resistant?
Agent: Yes! SCBE is quantum-resistant through multiple mechanisms:
• Post-Quantum Primitives: Uses lattice-based and hash-based crypto
• Quasicrystal Lattice: Provides quantum-resistant key exchange
...

You: back
```

### Example 2: Get Code Examples

```bash
agent> code
Available languages:
  1. Python
  2. TypeScript

Select language (1-2): 1

🐍 PYTHON EXAMPLES
============================================================

1. ENCRYPT MESSAGE
------------------------------------------------------------
from symphonic_cipher import SymphonicCipher

cipher = SymphonicCipher()
encrypted = cipher.encrypt("Hello, World!", "my-secret-key")
print(f"Encrypted: {encrypted}")
...
```

### Example 3: Scan Code for Vulnerabilities

```bash
agent> scan
Paste your code (press Ctrl+D when done):
------------------------------------------------------------
password = "hardcoded123"
user_input = request.get('query')
db.execute(f"SELECT * FROM users WHERE name = '{user_input}'")
^D

🔍 Scanning for vulnerabilities...

⚠️  FOUND 2 VULNERABILITIES:

1. HIGH: Hardcoded credentials
   Line 1: Credentials should not be in source code
   Fix: Use environment variables or secure vaults

2. HIGH: Potential SQL injection
   Line 3: String concatenation in SQL queries
   Fix: Use parameterized queries
```

### Example 4: Secure Web Search

```bash
agent> search
Search: SCBE documentation
🔐 Encrypting query with SCBE...
✓ Found 3 results

1. SCBE Documentation - Official Docs
   https://scbe-aethermoore.dev/docs
   Complete guide to SCBE-AETHERMOORE security framework...
```

## AI Assistant Topics

The AI assistant can help with:

- **SCBE Basics**: What it is, how it works
- **Security**: Quantum resistance, attack defense
- **Implementation**: Python and TypeScript code
- **Integration**: How to use SCBE in your projects
- **Best Practices**: Security guidelines
- **Troubleshooting**: Common issues and solutions

## Security Scanner Rules

The scanner checks for:

### Critical Vulnerabilities
- `eval()` usage - Can execute arbitrary code
- `exec()` usage - Can execute arbitrary code

### High Severity
- Hardcoded credentials (passwords, API keys, tokens)
- SQL injection risks (string concatenation in queries)

### Medium Severity
- Insecure random number generation
- Command injection risks (os.system, subprocess)

## Integration with CLI

Use the unified launcher to switch between CLI and Agent:

```bash
# Windows
scbe.bat cli    # Interactive CLI
scbe.bat agent  # AI Agent
scbe.bat demo   # Run demo

# Unix/Linux/Mac
./scbe cli
./scbe agent
./scbe demo
```

## Tips

1. **Ask Natural Questions**: The AI understands conversational language
2. **Use Scan Regularly**: Check your code before committing
3. **Explore Code Examples**: Copy-paste examples to get started quickly
4. **Search Securely**: Your queries are encrypted with SCBE
5. **Learn Interactively**: Ask follow-up questions to dive deeper

## Architecture

```
scbe-agent.py
├── AI Chat (ask)
│   ├── SCBE knowledge base
│   ├── Cryptography concepts
│   └── Coding assistance
├── Web Search (search)
│   ├── Query encryption with SCBE
│   └── Secure result retrieval
├── Code Library (code)
│   ├── Python examples
│   └── TypeScript examples
└── Security Scanner (scan)
    ├── Vulnerability detection
    ├── Severity classification
    └── Fix recommendations
```

## FAQ

**Q: Is the AI online or offline?**
A: The current version uses local knowledge. Future versions will support online AI models.

**Q: Does the security scanner replace real security audits?**
A: No, it's a helpful tool but not a replacement for professional security audits.

**Q: Can I add my own code examples?**
A: Yes! Edit the `_init_code_library()` method in `scbe-agent.py`.

**Q: Is web search really encrypted?**
A: Yes, queries are encrypted with SCBE before being sent (demo implementation).

## Next Steps

1. Try the AI assistant: `python scbe-agent.py`
2. Ask questions about SCBE
3. Scan your code for vulnerabilities
4. Explore code examples
5. Integrate SCBE into your projects

## Support

- Documentation: See `README.md` and `COMPLETE_SYSTEM.md`
- CLI Guide: See `CLI_README.md`
- Quick Reference: See `SCBE_CHEATSHEET.md`

---

**Stay secure! 🛡️**
