# SCBE-AETHERMOORE Tech Stack

## Languages

- **TypeScript** (primary) - Core modules, cryptographic operations
- **Python** (secondary) - Physics simulation, cipher implementations, API
- **JavaScript** - Lambda functions, demos

## Runtime Requirements

- Node.js >= 18.0.0
- Python 3.10+

## Build System

- **TypeScript**: `tsc` compiler with `tsconfig.json`
- **Python**: pip with `requirements.txt`, optional `pyproject.toml`
- **Package Manager**: npm (Node), pip (Python)

## Testing Frameworks

### TypeScript
- **Vitest** - Unit and integration tests
- **fast-check** - Property-based testing (minimum 100 iterations)

### Python
- **pytest** - Unit and integration tests
- **hypothesis** - Property-based testing (minimum 100 iterations)
- **pytest-cov** - Coverage reporting

## Key Dependencies

### TypeScript
- `fast-check` - Property-based testing
- `vitest` - Test runner
- `typescript` ^5.4

### Python
- `numpy`, `scipy` - Numerical computing, hyperbolic geometry
- `cryptography`, `pynacl`, `pycryptodome` - Cryptographic primitives
- `argon2-cffi` - KDF for RWP v3.0
- `boto3` - AWS Lambda deployment
- `hypothesis` - Property-based testing

## Common Commands

```bash
# Build
npm run build              # Compile TypeScript
npm run clean              # Remove dist/

# Test
npm test                   # Run TypeScript tests (vitest)
npm run test:python        # Run Python tests (pytest)
npm run test:all           # Run all tests

# Type checking
npm run typecheck          # TypeScript type check

# Formatting
npm run format             # Format TypeScript (prettier)
npm run format:python      # Format Python (black)

# Linting
npm run lint               # Lint TypeScript
npm run lint:python        # Lint Python (flake8)

# Python tests directly
pytest tests/ -v                    # All tests
pytest -m quantum tests/            # By marker
pytest tests/ --cov=src             # With coverage

# CLI tools
python scbe-cli.py         # Interactive CLI
python scbe-agent.py       # AI coding assistant
python demo.py             # Run demo

# Docker
npm run docker:build       # Build container
npm run docker:compose     # Start with docker-compose
```

## Test Markers (pytest)

- `@pytest.mark.quantum` - Quantum attack tests
- `@pytest.mark.ai_safety` - AI safety tests
- `@pytest.mark.compliance` - Compliance tests
- `@pytest.mark.property` - Property-based tests
- `@pytest.mark.slow` - Long-running tests (>1 minute)

## Coverage Target

95% coverage for lines, functions, branches, and statements.
