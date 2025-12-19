#!/bin/bash
# Helper script for publishing instancepedia to PyPI
# Usage: ./scripts/publish.sh [testpypi|pypi]

set -e

REPOSITORY="${1:-testpypi}"

if [[ "$REPOSITORY" != "testpypi" && "$REPOSITORY" != "pypi" ]]; then
    echo "Usage: $0 [testpypi|pypi]"
    echo "  testpypi - Publish to TestPyPI (default)"
    echo "  pypi     - Publish to PyPI"
    exit 1
fi

echo "🚀 Publishing instancepedia to $REPOSITORY..."
echo ""

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info

# Build package
echo "📦 Building package..."
python3 -m build

# Check package
echo "✅ Checking package..."
python3 -m twine check dist/*

# Upload
echo "📤 Uploading to $REPOSITORY..."
if [[ "$REPOSITORY" == "testpypi" ]]; then
    python3 -m twine upload --repository testpypi dist/*
else
    python3 -m twine upload --repository pypi dist/*
fi

echo ""
echo "✅ Successfully published to $REPOSITORY!"
echo ""
if [[ "$REPOSITORY" == "testpypi" ]]; then
    echo "Test installation with:"
    echo "  pip install --index-url https://test.pypi.org/simple/ instancepedia"
else
    echo "Install with:"
    echo "  pip install instancepedia"
fi
