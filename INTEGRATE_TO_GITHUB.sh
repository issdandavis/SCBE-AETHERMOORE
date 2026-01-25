#!/bin/bash
#
# Integration Script: Copy SCBE Production Pack → SCBE-AETHERMOORE GitHub Repo
#
# Usage:
#   1. Update GITHUB_REPO_PATH below to point to your cloned repo
#   2. Run: bash INTEGRATE_TO_GITHUB.sh
#   3. Review changes
#   4. Commit and push to GitHub
#

set -e  # Exit on error

# Configuration
GITHUB_REPO_PATH="C:/Users/issda/Downloads/SCBE-AETHERMOORE"
CURRENT_DIR="$(pwd)"

echo "=================================================="
echo "SCBE Production Pack → GitHub Integration"
echo "=================================================="
echo ""
echo "Source: $CURRENT_DIR"
echo "Target: $GITHUB_REPO_PATH"
echo ""

# Check if GitHub repo exists
if [ ! -d "$GITHUB_REPO_PATH" ]; then
    echo "ERROR: GitHub repo not found at $GITHUB_REPO_PATH"
    echo ""
    echo "Please clone it first:"
    echo "  cd C:/Users/issda/Downloads"
    echo "  git clone https://github.com/issdandavis/SCBE-AETHERMOORE.git"
    exit 1
fi

echo "Step 1: Creating directory structure..."
mkdir -p "$GITHUB_REPO_PATH/symphonic_cipher/core"
mkdir -p "$GITHUB_REPO_PATH/symphonic_cipher/geoseal"
mkdir -p "$GITHUB_REPO_PATH/symphonic_cipher/spiralverse/tongues"
mkdir -p "$GITHUB_REPO_PATH/symphonic_cipher/pqc"
mkdir -p "$GITHUB_REPO_PATH/symphonic_cipher/topology"
mkdir -p "$GITHUB_REPO_PATH/symphonic_cipher/dynamics"
mkdir -p "$GITHUB_REPO_PATH/symphonic_cipher/connectors"
mkdir -p "$GITHUB_REPO_PATH/symphonic_cipher/audio"
mkdir -p "$GITHUB_REPO_PATH/scbe"
mkdir -p "$GITHUB_REPO_PATH/tests"
mkdir -p "$GITHUB_REPO_PATH/examples"
mkdir -p "$GITHUB_REPO_PATH/docs"
mkdir -p "$GITHUB_REPO_PATH/config"

echo "✓ Directory structure created"
echo ""

echo "Step 2: Copying core SCBE implementation..."
cp "src/scbe_14layer_reference.py" "$GITHUB_REPO_PATH/scbe/pipeline.py"
echo "✓ scbe/pipeline.py"
echo ""

echo "Step 3: Copying GeoSeal manifold..."
cp "symphonic_cipher_geoseal_manifold.py" "$GITHUB_REPO_PATH/symphonic_cipher/geoseal/manifold.py"
echo "✓ symphonic_cipher/geoseal/manifold.py"
echo ""

echo "Step 4: Copying Spiralverse SDK..."
cp "symphonic_cipher_spiralverse_sdk.py" "$GITHUB_REPO_PATH/symphonic_cipher/spiralverse/sdk.py"
echo "✓ symphonic_cipher/spiralverse/sdk.py"
echo ""

echo "Step 5: Copying tests..."
cp "tests/test_scbe_14layers.py" "$GITHUB_REPO_PATH/tests/"
echo "✓ tests/test_scbe_14layers.py"
echo ""

echo "Step 6: Copying examples..."
cp "examples/demo_integrated_system.py" "$GITHUB_REPO_PATH/examples/"
cp "examples/demo_scbe_system.py" "$GITHUB_REPO_PATH/examples/"
echo "✓ examples/demo_integrated_system.py"
echo "✓ examples/demo_scbe_system.py"
echo ""

echo "Step 7: Copying documentation..."
cp "docs/WHAT_YOU_BUILT.md" "$GITHUB_REPO_PATH/docs/"
cp "docs/GEOSEAL_CONCEPT.md" "$GITHUB_REPO_PATH/docs/"
cp "docs/DEMONSTRATION_SUMMARY.md" "$GITHUB_REPO_PATH/docs/"
cp "docs/AWS_LAMBDA_DEPLOYMENT.md" "$GITHUB_REPO_PATH/docs/"
cp "docs/COMPREHENSIVE_MATH_SCBE.md" "$GITHUB_REPO_PATH/docs/"
cp "docs/LANGUES_WEIGHTING_SYSTEM.md" "$GITHUB_REPO_PATH/docs/"
cp "docs/GITHUB_INTEGRATION_GUIDE.md" "$GITHUB_REPO_PATH/docs/"
echo "✓ Documentation files copied"
echo ""

echo "Step 8: Copying configuration..."
if [ -f "config/scbe.alerts.yml" ]; then
    cp "config/scbe.alerts.yml" "$GITHUB_REPO_PATH/config/"
    cp "config/sentinel.yml" "$GITHUB_REPO_PATH/config/"
    cp "config/steward.yml" "$GITHUB_REPO_PATH/config/"
    echo "✓ Configuration files copied"
else
    echo "⚠ Configuration files not found (optional)"
fi
echo ""

echo "Step 9: Copying README..."
cp "README.md" "$GITHUB_REPO_PATH/"
echo "✓ README.md"
echo ""

echo "Step 10: Creating __init__.py files..."

# Root package
cat > "$GITHUB_REPO_PATH/symphonic_cipher/__init__.py" << 'EOF'
"""
SCBE-AETHERMOORE v3.0 - Symphonic Cipher Library
Patent Pending: USPTO #63/961,403

Quantum-Resistant Hyperbolic Geometry AI Safety Framework
"""

__version__ = "3.0.0"
__author__ = "Issac Davis"
__patent__ = "USPTO #63/961,403"

# Core components
from .geoseal.manifold import GeoSealManifold
from .spiralverse.sdk import SpiralverseSDK, SacredTongue

__all__ = [
    'GeoSealManifold',
    'SpiralverseSDK',
    'SacredTongue',
]
EOF

# GeoSeal package
cat > "$GITHUB_REPO_PATH/symphonic_cipher/geoseal/__init__.py" << 'EOF'
"""GeoSeal Geometric Trust Manifold"""
from .manifold import GeoSealManifold

__all__ = ['GeoSealManifold']
EOF

# Spiralverse package
cat > "$GITHUB_REPO_PATH/symphonic_cipher/spiralverse/__init__.py" << 'EOF'
"""Spiralverse Protocol with Six Sacred Tongues"""
from .sdk import SpiralverseSDK, SacredTongue

__all__ = ['SpiralverseSDK', 'SacredTongue']
EOF

# Empty __init__.py for other packages
touch "$GITHUB_REPO_PATH/symphonic_cipher/core/__init__.py"
touch "$GITHUB_REPO_PATH/symphonic_cipher/pqc/__init__.py"
touch "$GITHUB_REPO_PATH/symphonic_cipher/topology/__init__.py"
touch "$GITHUB_REPO_PATH/symphonic_cipher/dynamics/__init__.py"
touch "$GITHUB_REPO_PATH/symphonic_cipher/connectors/__init__.py"
touch "$GITHUB_REPO_PATH/symphonic_cipher/audio/__init__.py"
touch "$GITHUB_REPO_PATH/symphonic_cipher/spiralverse/tongues/__init__.py"
touch "$GITHUB_REPO_PATH/scbe/__init__.py"

echo "✓ __init__.py files created"
echo ""

echo "Step 11: Creating KIRO system map..."
cp "KIRO_SYSTEM_MAP.md" "$GITHUB_REPO_PATH/"
echo "✓ KIRO_SYSTEM_MAP.md"
echo ""

echo "=================================================="
echo "Integration Complete!"
echo "=================================================="
echo ""
echo "Files copied to: $GITHUB_REPO_PATH"
echo ""
echo "Next steps:"
echo "  1. Review the changes:"
echo "     cd $GITHUB_REPO_PATH"
echo "     git status"
echo ""
echo "  2. Test the integration:"
echo "     python examples/demo_integrated_system.py"
echo ""
echo "  3. Commit and push:"
echo "     git add ."
echo "     git commit -m \"Complete integration: SCBE + GeoSeal + Spiralverse\""
echo "     git push origin main"
echo ""
echo "  4. View on GitHub:"
echo "     https://github.com/issdandavis/SCBE-AETHERMOORE"
echo ""
