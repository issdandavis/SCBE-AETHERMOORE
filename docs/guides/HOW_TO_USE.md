# How to Use SCBE-AETHERMOORE Package

## Install the Package

Open your terminal (Command Prompt) and type:

```bash
npm install git+https://github.com/issdandavis/scbe-aethermoore-demo.git
```

Wait for it to finish.

---

## Use in Node.js

### Option 1: Quick Test in Terminal

Open Command Prompt and type:

```bash
node
```

Then copy and paste this:

```javascript
const scbe = require('@scbe/aethermoore');
const { Feistel } = require('@scbe/aethermoore/symphonic');

// Check it loaded
console.log('SCBE Version:', scbe.VERSION);

// Create a Symphonic Cipher
const cipher = new Feistel();

// Encrypt a message
const encrypted = cipher.encryptString('Hello World', 'my-secret-key');
console.log('Encrypted:', Buffer.from(encrypted).toString('hex'));

// Decrypt it back
const decrypted = cipher.decryptString(encrypted, 'my-secret-key');
console.log('Decrypted:', decrypted);
```

Press Enter. You should see your message encrypted and decrypted!

**Recommended import style** (subpath imports):

```javascript
// Import specific modules directly
const { Feistel, FFT, HybridCrypto } = require('@scbe/aethermoore/symphonic');
const { BloomFilter, HKDF } = require('@scbe/aethermoore/crypto');
```

**Alternative import style** (namespace export in v3.0.0+ builds):

```javascript
const scbe = require('@scbe/aethermoore');
const cipher = new scbe.symphonic.Feistel();
```

---

### Option 2: Create a JavaScript File

1. Create a new file called `test.js`
2. Copy this code into it:

```javascript
// Example 1: Feistel Cipher
console.log('=== Feistel Cipher Demo ===');
const { Feistel, FFT, HybridCrypto } = require('@scbe/aethermoore/symphonic');
const feistel = new Feistel({ rounds: 6 });
const message = 'Secret Message';
const key = 'my-password-123';

const encrypted = feistel.encryptString(message, key);
console.log('Original:', message);
console.log('Encrypted:', Buffer.from(encrypted).toString('hex'));

const decrypted = feistel.decryptString(encrypted, key);
console.log('Decrypted:', decrypted);
console.log('Match:', message === decrypted ? '✓' : '✗');

// Example 2: FFT (Frequency Analysis)
console.log('\n=== FFT Demo ===');
const fft = new FFT();
const signal = [1, 0, -1, 0]; // Simple wave
const spectrum = fft.forward(signal);
console.log(
  'Frequency Spectrum:',
  spectrum.map((c) => c.magnitude().toFixed(2))
);

// Example 3: Hybrid Crypto (PQC + Classical)
console.log('\n=== Hybrid Crypto Demo ===');
const hybrid = new HybridCrypto();
const data = 'Top Secret Data';
const hybridEncrypted = hybrid.encrypt(data, key);
console.log('Hybrid Encrypted Length:', hybridEncrypted.length);
const hybridDecrypted = hybrid.decrypt(hybridEncrypted, key);
console.log('Hybrid Decrypted:', hybridDecrypted);
console.log('Match:', data === hybridDecrypted ? '✓' : '✗');
```

3. Run it in terminal:

```bash
node test.js
```

---

## Available Components

Your package includes:

### Symphonic Cipher

- `Feistel` - Balanced Feistel network encryption
- `FFT` - Fast Fourier Transform for frequency analysis
- `Complex` - Complex number math
- `ZBase32` - Human-friendly encoding
- `HybridCrypto` - Post-quantum + classical encryption
- `SymphonicAgent` - AI agent with encryption

### Crypto Tools

- `BloomFilter` - Probabilistic data structure
- `Envelope` - Secure message envelopes
- `HKDF` - Key derivation
- `NonceManager` - Nonce generation
- `ReplayGuard` - Prevent replay attacks

### Self-Healing

- `QuickFixBot` - Auto-fix common issues
- `DeepHealing` - Advanced recovery
- `Coordinator` - Orchestrate healing

### Rollout

- `CanaryDeployment` - Gradual rollouts
- `CircuitBreaker` - Fault tolerance

---

## Simple Examples

### Encrypt/Decrypt Text

```javascript
const { Feistel } = require('@scbe/aethermoore/symphonic');
const cipher = new Feistel();
const encrypted = cipher.encryptString('Hello', 'password');
const decrypted = cipher.decryptString(encrypted, 'password');
```

### Analyze Frequencies

```javascript
const { FFT } = require('@scbe/aethermoore/symphonic');
const fft = new FFT();
const spectrum = fft.forward([1, 2, 3, 4]);
```

### Create AI Agent

```javascript
const { SymphonicAgent } = require('@scbe/aethermoore/symphonic');
const agent = new SymphonicAgent('agent-1');
const result = agent.processIntent({ action: 'encrypt', data: 'secret' });
```

---

## Need Help?

- Check the `examples/` folder for more code samples
- Read `README.md` for full documentation
- Run tests: `npm test`

---

## Troubleshooting

**Error: Cannot find module '@scbe/aethermoore'**

- Make sure you ran: `npm install git+https://github.com/issdandavis/scbe-aethermoore-demo.git`
- Check that `node_modules/@scbe/aethermoore` folder exists

**Error: crypto module not found**

- You need Node.js version 18 or higher
- Check version: `node --version`

**Import errors**

- Use `require()` not `import` (unless using ES modules)
- Prefer subpath imports: `require('@scbe/aethermoore/symphonic')`
- If you use `require('@scbe/aethermoore').symphonic`, ensure you're on v3.0.0+ builds
