# SCBE-AETHERMOORE v3.0.0 - Installation Guide

**Complete installation guide organized by layers and dependencies**

---

## Quick Start (5 Minutes)

```bash
# 1. Clone repository
git clone https://github.com/issdandavis/scbe-aethermoore-demo.git
cd scbe-aethermoore-demo

# 2. Run unified build script
./BUILD.bat  # Windows
# or
./BUILD.sh   # Linux/Mac

# 3. Verify installation
npm test
python -m pytest tests/ -v
```

---

## System Requirements

### Minimum Requirements
- **Node.js**: 18.0.0 or higher
- **Python**: 3.10 or higher
- **npm**: 8.0.0 or higher
- **pip**: 21.0.0 or higher
- **RAM**: 4 GB minimum, 8 GB recommended
- **Disk Space**: 2 GB for dependencies

### Supported Platforms
- ✅ Windows 10/11 (x64)
- ✅ macOS 11+ (Intel/Apple Silicon)
- ✅ Linux (Ubuntu 20.04+, Debian 11+, RHEL 8+)

---

## Installation by Layer

### Layer 0: Environment Setup

#### Step 1: Install Node.js

**Windows**:
```bash
# Download from https://nodejs.org/
# Or use Chocolatey:
choco install nodejs
```

**macOS**:
```bash
brew install node
```

**Linux**:
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

#### Step 2: Install Python

**Windows**:
```bash
# Download from https://www.python.org/downloads/
# Or use Chocolatey:
choco install python
```

**macOS**:
```bash
brew install python@3.11
```

**Linux**:
```bash
sudo apt-get update
sudo apt-get install python3.11 python3-pip
```

#### Step 3: Verify Installation

```bash
node --version  # Should be >= 18.0.0
npm --version   # Should be >= 8.0.0
python --version  # Should be >= 3.10
pip --version   # Should be >= 21.0.0
```

---

### Layer 1: Core Dependencies

#### TypeScript/JavaScript Dependencies

```bash
npm install
```

**Key Packages Installed**:
- `typescript@^5.4.0` - TypeScript compiler
- `vitest@^4.0.17` - Testing framework
- `fast-check@^4.5.3` - Property-based testing
- `@types/node@^20.11.0` - Node.js type definitions

#### Python Dependencies

```bash
pip install -r requirements.txt
```

**Key Packages Installed**:
- `numpy>=1.24.0` - Numerical computing
- `scipy>=1.10.0` - Scientific computing
- `cryptography>=41.0.0` - Cryptographic primitives
- `pytest>=7.4.0` - Testing framework
- `hypothesis>=6.82.0` - Property-based testing

---

### Layer 2: SCBE Core Modules

#### Layer 2.1: Cryptographic Primitives (src/crypto/)

**Files**:
- `bloom.ts` - Bloom filter for replay protection
- `envelope.ts` - Encrypted envelope format
- `hkdf.ts` - HMAC-based Key Derivation Function
- `jcs.ts` - JSON Canonical Serialization
- `kms.ts` - Key Management System interface
- `nonceManager.ts` - Nonce generation and tracking
- `replayGuard.ts` - Replay attack prevention

**Build**:
```bash
npm run build:src
```

**Verify**:
```bash
ls dist/src/crypto/  # Should show compiled .js and .d.ts files
```

#### Layer 2.2: Python Cryptographic Modules (src/crypto/)

**Files**:
- `rwp_v3.py` - RWP v3.0 Protocol (Argon2id + XChaCha20-Poly1305)
- `sacred_tongues.py` - Sacred Tongue tokenization (6 tongues × 256 tokens)

**Verify**:
```bash
python -c "from src.crypto.rwp_v3 import RWPv3; print('RWP v3.0 loaded')"
python -c "from src.crypto.sacred_tongues import SacredTongueTokenizer; print('Sacred Tongues loaded')"
```

---

### Layer 3: Harmonic & Geometric Modules

#### Layer 3.1: Harmonic Scaling (src/harmonic/)

**TypeScript Files**:
- `assertions.ts` - Mathematical invariant checks
- `audioAxis.ts` - Audio telemetry (Layer 14)
- `constants.ts` - Physical constants
- `halAttention.ts` - HAL attention coupling matrix
- `hamiltonianCFI.ts` - Hamiltonian CFI (PHDM)
- `harmonicScaling.ts` - Harmonic scaling law
- `hyperbolic.ts` - Hyperbolic geometry (Poincaré ball)
- `languesMetric.ts` - Langues weighting system
- `phdm.ts` - Polyhedral Hamiltonian Defense Manifold
- `pqc.ts` - Post-quantum cryptography (ML-KEM, ML-DSA)
- `qcLattice.ts` - Quasicrystal lattice
- `sacredTongues.ts` - Sacred Tongues (TypeScript interface)
- `spiralSeal.ts` - Spiral Seal (SS1)
- `vacuumAcoustics.ts` - Vacuum acoustics (bottle beam)

**Build**:
```bash
npm run build:src
```

**Test**:
```bash
npm test tests/harmonic/
```

#### Layer 3.2: Python Harmonic Modules (src/harmonic/)

**Files**:
- `context_encoder.py` - SCBE context encoding (Layers 1-4)

**Verify**:
```bash
python -c "from src.harmonic.context_encoder import ContextEncoder; print('Context Encoder loaded')"
```

---

### Layer 4: SCBE Context Encoding (src/scbe/)

**Files**:
- `context_encoder.py` - Complete SCBE context encoding pipeline

**Layers Implemented**:
1. **Layer 1**: Complex context vector c(t) ∈ ℂ^D
2. **Layer 2**: Realification x(t) = [ℜ(c), ℑ(c)]^T
3. **Layer 3**: Weighted transform x_G(t) = G^(1/2)x(t)
4. **Layer 4**: Poincaré embedding u(t) = tanh(||x_G||)x_G/||x_G||

**Test**:
```bash
python -m pytest tests/test_sacred_tongue_integration.py::test_scbe_context_encoder -v
```

---

### Layer 5: Spiralverse (RWP v3.0 + Policy Engine)

#### TypeScript Implementation (src/spiralverse/)

**Files**:
- `index.ts` - Main exports
- `rwp.ts` - RWP v3.0 TypeScript implementation
- `policy.ts` - Policy engine
- `types.ts` - Type definitions

**Build**:
```bash
npm run build:src
```

**Test**:
```bash
npm test tests/spiralverse/
```

---

### Layer 6: Symphonic Cipher

#### TypeScript Implementation (src/symphonic/)

**Files**:
- `Complex.ts` - Complex number arithmetic
- `FFT.ts` - Fast Fourier Transform
- `Feistel.ts` - Feistel network
- `HybridCrypto.ts` - Hybrid cryptography
- `SymphonicAgent.ts` - Symphonic agent
- `ZBase32.ts` - ZBase32 encoding
- `index.ts` - Main exports

**Build**:
```bash
npm run build:src
```

**Test**:
```bash
npm test tests/symphonic/
```

---

### Layer 7: Metrics & Telemetry

#### TypeScript Implementation (src/metrics/)

**Files**:
- `telemetry.ts` - Telemetry collection

**Build**:
```bash
npm run build:src
```

---

### Layer 8: Rollout & Deployment

#### TypeScript Implementation (src/rollout/)

**Files**:
- `canary.ts` - Canary deployment
- `circuitBreaker.ts` - Circuit breaker pattern

**Build**:
```bash
npm run build:src
```

---

### Layer 9: Self-Healing

#### TypeScript Implementation (src/selfHealing/)

**Files**:
- `coordinator.ts` - Self-healing coordinator
- `deepHealing.ts` - Deep healing strategies
- `quickFixBot.ts` - Quick fix bot

**Build**:
```bash
npm run build:src
```

---

## Complete Build Process

### Option 1: Unified Build Script (Recommended)

```bash
# Windows
BUILD.bat

# Linux/Mac
chmod +x BUILD.sh
./BUILD.sh
```

**What it does**:
1. Verifies environment (Node.js, Python, npm, pip)
2. Cleans previous builds
3. Installs Node.js dependencies
4. Installs Python dependencies
5. Builds TypeScript modules
6. Runs test suite (TypeScript + Python)
7. Packages npm module
8. Verifies build integrity

### Option 2: Manual Build

```bash
# 1. Clean
rm -rf dist node_modules __pycache__ .pytest_cache

# 2. Install dependencies
npm install
pip install -r requirements.txt

# 3. Build TypeScript
npm run build

# 4. Run tests
npm test
python -m pytest tests/ -v

# 5. Package
npm pack
```

---

## Verification

### TypeScript Verification

```bash
# Type check
npm run typecheck

# Run tests
npm test

# Check coverage
npm test -- --coverage
```

**Expected Output**:
```
✓ tests/harmonic/phdm.test.ts (7 tests)
✓ tests/spiralverse/rwp.test.ts (7 tests)
✓ tests/symphonic/*.test.ts (multiple tests)

Test Files  X passed (X)
     Tests  X passed (X)
```

### Python Verification

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test suite
python -m pytest tests/test_sacred_tongue_integration.py -v

# Check coverage
python -m pytest tests/ --cov=src --cov-report=term
```

**Expected Output**:
```
tests/test_sacred_tongue_integration.py::test_sacred_tongue_tokenizer PASSED
tests/test_sacred_tongue_integration.py::test_rwp_v3_encryption PASSED
tests/test_sacred_tongue_integration.py::test_scbe_context_encoder PASSED
...
======================== 17 passed in 43.79s ========================
```

### Package Verification

```bash
# Check package contents
tar -tzf scbe-aethermoore-3.0.0.tgz | head -20

# Test installation
npm install scbe-aethermoore-3.0.0.tgz
node -e "const scbe = require('scbe-aethermoore'); console.log('Package loaded successfully');"
```

---

## Troubleshooting

### Common Issues

#### Issue 1: Node.js version too old

**Error**: `error:0308010C:digital envelope routines::unsupported`

**Solution**:
```bash
# Upgrade Node.js to 18.0.0 or higher
nvm install 18
nvm use 18
```

#### Issue 2: Python module not found

**Error**: `ModuleNotFoundError: No module named 'numpy'`

**Solution**:
```bash
pip install -r requirements.txt
# Or install specific package:
pip install numpy scipy cryptography
```

#### Issue 3: TypeScript build fails

**Error**: `error TS2307: Cannot find module`

**Solution**:
```bash
# Clean and rebuild
rm -rf dist node_modules
npm install
npm run build
```

#### Issue 4: Tests fail with "pytest not found"

**Error**: `bash: pytest: command not found`

**Solution**:
```bash
# Install pytest
pip install pytest pytest-cov hypothesis

# Or use python -m pytest
python -m pytest tests/ -v
```

#### Issue 5: Permission denied on BUILD.bat

**Error**: `Permission denied: ./BUILD.bat`

**Solution**:
```bash
# Windows: Run as administrator
# Linux/Mac: Make executable
chmod +x BUILD.sh
./BUILD.sh
```

---

## Next Steps

After successful installation:

1. **Read Documentation**:
   - `README.md` - Project overview
   - `QUICKSTART.md` - 5-minute tutorial
   - `HOW_TO_USE.md` - Detailed usage guide
   - `ARCHITECTURE_5_LAYERS.md` - System architecture

2. **Run Demos**:
   ```bash
   # Python demos
   python examples/rwp_v3_sacred_tongue_demo.py
   
   # TypeScript demos
   npm run demo
   ```

3. **Explore Examples**:
   - `examples/rwp_v3_demo.py` - RWP v3.0 basic usage
   - `examples/rwp_v3_sacred_tongue_demo.py` - Sacred Tongue integration
   - `examples/demo_integrated_system.py` - Complete system demo

4. **Read Technical Documents**:
   - `SCBE_TOPOLOGICAL_CFI_UNIFIED.md` - Complete technical specification
   - `PATENT_PROVISIONAL_APPLICATION.md` - Patent application
   - `VERIFICATION_REPORT.md` - Test verification report

---

## Support

- **GitHub Issues**: https://github.com/issdandavis/scbe-aethermoore-demo/issues
- **npm Package**: https://www.npmjs.com/package/scbe-aethermoore
- **Documentation**: See `docs/` folder
- **Email**: issdandavis@gmail.com

---

**Installation Guide Version**: 3.0.0  
**Last Updated**: January 18, 2026  
**Status**: Production-Ready
