#!/bin/bash
# ============================================================================
# SCBE-AETHERMOORE v3.0.0 - Unified Build Script (Linux/Mac)
# ============================================================================
# This script handles complete installation, build, and verification
# for the SCBE-AETHERMOORE cryptographic framework.
#
# Author: Issac Daniel Davis
# Date: January 18, 2026
# License: MIT
# ============================================================================

echo ""
echo "============================================================================"
echo "SCBE-AETHERMOORE v3.0.0 - Unified Build System"
echo "============================================================================"
echo ""

# ============================================================================
# STEP 1: ENVIRONMENT VERIFICATION
# ============================================================================
echo "[STEP 1/8] Verifying environment..."
echo ""

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "[ERROR] Node.js not found. Please install Node.js 18.0.0 or higher."
    echo "Download: https://nodejs.org/"
    exit 1
fi

node --version
echo "[OK] Node.js found"

# Check npm
if ! command -v npm &> /dev/null; then
    echo "[ERROR] npm not found. Please install npm."
    exit 1
fi

npm --version
echo "[OK] npm found"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python not found. Please install Python 3.10 or higher."
    echo "Download: https://www.python.org/downloads/"
    exit 1
fi

python3 --version
echo "[OK] Python found"

# Check pip
if ! command -v pip3 &> /dev/null; then
    echo "[ERROR] pip not found. Please install pip."
    exit 1
fi

pip3 --version
echo "[OK] pip found"

echo ""
echo "[STEP 1/8] Environment verification complete!"
echo ""

# ============================================================================
# STEP 2: CLEAN PREVIOUS BUILDS
# ============================================================================
echo "[STEP 2/8] Cleaning previous builds..."
echo ""

rm -rf dist node_modules __pycache__ .pytest_cache htmlcov .coverage coverage.json *.tgz

echo "[OK] Clean complete"
echo ""

# ============================================================================
# STEP 3: INSTALL NODE.JS DEPENDENCIES
# ============================================================================
echo "[STEP 3/8] Installing Node.js dependencies..."
echo ""

npm install
if [ $? -ne 0 ]; then
    echo "[ERROR] npm install failed"
    exit 1
fi

echo "[OK] Node.js dependencies installed"
echo ""

# ============================================================================
# STEP 4: INSTALL PYTHON DEPENDENCIES
# ============================================================================
echo "[STEP 4/8] Installing Python dependencies..."
echo ""

pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[ERROR] pip install failed"
    exit 1
fi

echo "[OK] Python dependencies installed"
echo ""

# ============================================================================
# STEP 5: BUILD TYPESCRIPT MODULES
# ============================================================================
echo "[STEP 5/8] Building TypeScript modules..."
echo ""

npm run build
if [ $? -ne 0 ]; then
    echo "[ERROR] TypeScript build failed"
    exit 1
fi

echo "[OK] TypeScript build complete"
echo ""

# ============================================================================
# STEP 6: RUN TESTS
# ============================================================================
echo "[STEP 6/8] Running test suite..."
echo ""

TEST_FAILED=0

# TypeScript tests
echo "[6.1] Running TypeScript tests..."
npm test
if [ $? -ne 0 ]; then
    echo "[WARNING] TypeScript tests failed"
    TEST_FAILED=1
else
    echo "[OK] TypeScript tests passed"
fi
echo ""

# Python tests
echo "[6.2] Running Python tests..."
python3 -m pytest tests/ -v --tb=short
if [ $? -ne 0 ]; then
    echo "[WARNING] Python tests failed"
    TEST_FAILED=1
else
    echo "[OK] Python tests passed"
fi
echo ""

if [ $TEST_FAILED -eq 1 ]; then
    echo "[WARNING] Some tests failed. Review output above."
    echo ""
fi

# ============================================================================
# STEP 7: PACKAGE NPM MODULE
# ============================================================================
echo "[STEP 7/8] Packaging npm module..."
echo ""

npm pack
if [ $? -ne 0 ]; then
    echo "[ERROR] npm pack failed"
    exit 1
fi

echo "[OK] Package created: scbe-aethermoore-3.0.0.tgz"
echo ""

# ============================================================================
# STEP 8: VERIFICATION
# ============================================================================
echo "[STEP 8/8] Verifying build..."
echo ""

if [ ! -f "dist/src/index.js" ]; then
    echo "[ERROR] Build verification failed: dist/src/index.js not found"
    exit 1
fi

if [ ! -f "scbe-aethermoore-3.0.0.tgz" ]; then
    echo "[ERROR] Build verification failed: package tarball not found"
    exit 1
fi

echo "[OK] Build verification complete"
echo ""

# ============================================================================
# BUILD SUMMARY
# ============================================================================
echo "============================================================================"
echo "BUILD SUMMARY"
echo "============================================================================"
echo ""
echo "Status: SUCCESS"
echo "Package: scbe-aethermoore-3.0.0.tgz"
echo "Size:"
ls -lh scbe-aethermoore-3.0.0.tgz | awk '{print $5}'
echo ""
echo "TypeScript modules: dist/src/"
echo "Python modules: src/"
echo ""
echo "Next steps:"
echo "  1. Test installation: npm install scbe-aethermoore-3.0.0.tgz"
echo "  2. Run demos: npm run demo"
echo "  3. Publish to npm: npm publish --access public"
echo ""
echo "Documentation:"
echo "  - README.md (quick start)"
echo "  - QUICKSTART.md (5-minute tutorial)"
echo "  - HOW_TO_USE.md (detailed usage)"
echo "  - ARCHITECTURE_5_LAYERS.md (system architecture)"
echo ""
echo "============================================================================"
echo ""

if [ $TEST_FAILED -eq 1 ]; then
    echo "[WARNING] Build completed with test failures. Review test output."
    exit 2
fi

echo "[SUCCESS] Build completed successfully!"
exit 0
