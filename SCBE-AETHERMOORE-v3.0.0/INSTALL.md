# SCBE-AETHERMOORE v3.0.0 Installation

## Quick Start

### Prerequisites
- Node.js 18+
- npm or yarn
- Python 3.10+ (optional, for CLI tools)

### Installation

```bash
# 1. Install dependencies
npm install

# 2. Build the project
npm run build

# 3. Run tests (413 tests)
npx vitest run

# 4. Open the interactive demo
# Open demo/index.html in your browser
```

### Interactive Demo

The easiest way to explore SCBE-AETHERMOORE is through the interactive demo:

1. Open `demo/index.html` in any modern browser
2. Explore:
   - Poincare Ball visualization
   - 14-Layer Pipeline execution
   - Harmonic Scaling calculator
   - Six Sacred Tongues display
   - Post-Quantum Cryptography demo
   - Quasicrystal lattice visualization

### Python CLI

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run the CLI
python scbe-cli.py --help
```

### Docker

```bash
# Build and run with Docker
docker-compose up -d
```

## Package Contents

```
SCBE-AETHERMOORE-v3.0.0/
├── src/                    # TypeScript source code
│   └── harmonic/          # Core 14-layer implementation
│       ├── pqc.ts         # Post-Quantum Cryptography
│       ├── qcLattice.ts   # Quasicrystal Lattice
│       ├── hyperbolic.ts  # Poincare Ball geometry
│       └── ...            # Other modules
├── tests/                  # Test suite (413 tests)
├── demo/                   # Interactive browser demo
├── docs/                   # Documentation
├── examples/               # Example implementations
└── config/                 # Configuration files
```

## Test Suite

```bash
# Run all tests
npx vitest run

# Run specific test file
npx vitest run tests/harmonic/pqc.test.ts

# Run tests in watch mode
npx vitest
```

## License

MIT License - See LICENSE file
