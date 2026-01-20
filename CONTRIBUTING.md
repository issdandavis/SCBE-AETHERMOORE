# Contributing to SCBE-AETHERMOORE

Thank you for your interest in contributing to SCBE-AETHERMOORE! This document provides guidelines and instructions for contributing.

## 🌟 Ways to Contribute

- **Bug Reports**: Found a bug? Open an issue with detailed reproduction steps
- **Feature Requests**: Have an idea? Share it in the discussions
- **Code Contributions**: Submit pull requests for bug fixes or new features
- **Documentation**: Improve docs, add examples, fix typos
- **Testing**: Write tests, improve coverage, report edge cases
- **Security**: Report security vulnerabilities responsibly

## 🚀 Getting Started

### Prerequisites

- **Node.js**: >= 18.0.0
- **Python**: >= 3.9
- **Git**: Latest version
- **npm**: Comes with Node.js

### Setup Development Environment

1. **Fork and Clone**

   ```bash
   git clone https://github.com/YOUR_USERNAME/scbe-aethermoore.git
   cd scbe-aethermoore
   ```

2. **Install Dependencies**

   ```bash
   # Node.js dependencies
   npm install

   # Python dependencies
   pip install -r requirements.txt
   pip install pytest pytest-cov hypothesis black flake8 mypy
   ```

3. **Build the Project**

   ```bash
   npm run build
   ```

4. **Run Tests**

   ```bash
   # TypeScript tests
   npm test

   # Python tests
   pytest tests/ -v
   ```

## 📝 Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

Branch naming conventions:

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `test/` - Test additions/improvements
- `refactor/` - Code refactoring

### 2. Make Your Changes

- Write clean, readable code
- Follow existing code style
- Add tests for new functionality
- Update documentation as needed

### 3. Test Your Changes

```bash
# Type check
npm run typecheck

# Build
npm run build

# Run all tests
npm test
pytest tests/ -v

# Format code
npm run format
black src/ tests/
```

### 4. Commit Your Changes

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
git commit -m "feat: add new encryption mode"
git commit -m "fix: resolve memory leak in layer 7"
git commit -m "docs: update API examples"
git commit -m "test: add property-based tests for harmonic scaling"
```

Commit types:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:

- Clear title and description
- Reference any related issues
- Screenshots/demos if applicable
- Test results

## 🎯 Code Style Guidelines

### TypeScript

- Use TypeScript strict mode
- Prefer `const` over `let`
- Use meaningful variable names
- Add JSDoc comments for public APIs
- Follow existing patterns in the codebase

```typescript
/**
 * Encrypts data using SCBE 14-layer architecture
 * @param plaintext - The data to encrypt
 * @param key - Encryption key
 * @returns Encrypted ciphertext
 */
export function encrypt(plaintext: string, key: string): string {
  // Implementation
}
```

### Python

- Follow PEP 8 style guide
- Use type hints
- Add docstrings for functions and classes
- Use Black for formatting (120 char line length)

```python
def encrypt(plaintext: str, key: str) -> str:
    """
    Encrypts data using SCBE 14-layer architecture.

    Args:
        plaintext: The data to encrypt
        key: Encryption key

    Returns:
        Encrypted ciphertext
    """
    # Implementation
```

## 🧪 Testing Guidelines

### Unit Tests

- Test individual functions and classes
- Use descriptive test names
- Cover edge cases and error conditions
- Aim for >80% code coverage

```typescript
describe('encrypt', () => {
  it('should encrypt plaintext with valid key', () => {
    const result = encrypt('hello', 'key123');
    expect(result).toBeDefined();
  });

  it('should throw error for empty key', () => {
    expect(() => encrypt('hello', '')).toThrow();
  });
});
```

### Property-Based Tests

- Use Hypothesis (Python) or fast-check (TypeScript)
- Test universal properties
- Let the framework find edge cases

```python
from hypothesis import given, strategies as st

@given(st.text(), st.text(min_size=1))
def test_encrypt_decrypt_roundtrip(plaintext: str, key: str):
    """Encryption followed by decryption should return original text"""
    ciphertext = encrypt(plaintext, key)
    result = decrypt(ciphertext, key)
    assert result == plaintext
```

## 📚 Documentation

- Update README.md for user-facing changes
- Add JSDoc/docstrings for new APIs
- Update CHANGELOG.md
- Add examples for new features
- Keep docs in sync with code

## 🔒 Security

### Reporting Security Issues

**DO NOT** open public issues for security vulnerabilities.

Instead, email: issdandavis@gmail.com

Include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will respond within 48 hours.

### Security Best Practices

- Never commit secrets or keys
- Use secure random number generation
- Validate all inputs
- Follow cryptographic best practices
- Keep dependencies updated

## 🏗️ Architecture Guidelines

### 14-Layer Architecture

When modifying layers, ensure:

- Mathematical correctness
- Backward compatibility
- Performance impact is measured
- Tests cover the changes

### Adding New Layers

1. Document the mathematical foundation
2. Implement with tests
3. Update architecture diagrams
4. Add to documentation
5. Benchmark performance

## 📋 Pull Request Checklist

Before submitting, ensure:

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] No merge conflicts
- [ ] Commit messages follow conventions
- [ ] PR description is clear and complete

## 🤝 Code Review Process

1. **Automated Checks**: CI/CD runs tests and linters
2. **Maintainer Review**: Core team reviews code
3. **Feedback**: Address review comments
4. **Approval**: At least one maintainer approval required
5. **Merge**: Squash and merge to main

## 📞 Getting Help

- **Discussions**: Ask questions in GitHub Discussions
- **Issues**: Report bugs or request features
- **Email**: issdandavis@gmail.com

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🙏 Recognition

Contributors will be recognized in:

- CHANGELOG.md
- GitHub contributors page
- Release notes

Thank you for contributing to SCBE-AETHERMOORE! 🚀
