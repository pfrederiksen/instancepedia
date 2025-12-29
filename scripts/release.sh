#!/bin/bash
# Automated release script for instancepedia
# Usage: ./scripts/release.sh [patch|minor|major|VERSION]
#   patch  - Bump patch version (0.1.1 -> 0.1.2)
#   minor  - Bump minor version (0.1.1 -> 0.2.0)
#   major  - Bump major version (0.1.1 -> 1.0.0)
#   VERSION - Use specific version (e.g., 0.1.5)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYPROJECT_FILE="$PROJECT_ROOT/pyproject.toml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
info() { echo -e "${BLUE}ℹ${NC} $1"; }
success() { echo -e "${GREEN}✓${NC} $1"; }
warning() { echo -e "${YELLOW}⚠${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; }

# Function to extract current version from pyproject.toml
get_current_version() {
    # Use Python to reliably parse TOML
    python3 << 'PYTHON_EOF'
import re
with open('pyproject.toml', 'r') as f:
    content = f.read()
    match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
    if match:
        print(match.group(1))
    else:
        # Fallback: try without quotes
        match = re.search(r'^version\s*=\s*(\S+)', content, re.MULTILINE)
        if match:
            print(match.group(1).strip())
PYTHON_EOF
}

# Function to bump version
bump_version() {
    local current_version=$1
    local bump_type=$2
    
    IFS='.' read -ra VERSION_PARTS <<< "$current_version"
    local major=${VERSION_PARTS[0]:-0}
    local minor=${VERSION_PARTS[1]:-0}
    local patch=${VERSION_PARTS[2]:-0}
    
    case $bump_type in
        major)
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        minor)
            minor=$((minor + 1))
            patch=0
            ;;
        patch)
            patch=$((patch + 1))
            ;;
        *)
            error "Invalid bump type: $bump_type"
            exit 1
            ;;
    esac
    
    echo "$major.$minor.$patch"
}

# Function to update version in pyproject.toml
update_version() {
    local new_version=$1
    local temp_file=$(mktemp)
    
    # Update version in pyproject.toml
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/^version = .*/version = \"$new_version\"/" "$PYPROJECT_FILE"
    else
        # Linux
        sed -i "s/^version = .*/version = \"$new_version\"/" "$PYPROJECT_FILE"
    fi
    
    success "Updated version in pyproject.toml to $new_version"
}

# Function to validate version format
validate_version() {
    local version=$1
    if [[ ! $version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        error "Invalid version format: $version (expected: X.Y.Z)"
        exit 1
    fi
}

# Parse arguments
if [ $# -eq 0 ]; then
    error "Usage: $0 [patch|minor|major|VERSION]"
    echo ""
    echo "Examples:"
    echo "  $0 patch          # Bump patch version (0.1.1 -> 0.1.2)"
    echo "  $0 minor          # Bump minor version (0.1.1 -> 0.2.0)"
    echo "  $0 major          # Bump major version (0.1.1 -> 1.0.0)"
    echo "  $0 0.2.0          # Use specific version"
    exit 1
fi

BUMP_TYPE=$1
cd "$PROJECT_ROOT"

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    error "Not in a git repository"
    exit 1
fi

# Get current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Verify we're on main branch (best practice)
if [ "$CURRENT_BRANCH" != "main" ] && [ "$CURRENT_BRANCH" != "master" ]; then
    error "Not on main/master branch. Current branch: $CURRENT_BRANCH"
    echo ""
    echo "Releases should be created from the main branch."
    echo "Please checkout main and try again:"
    echo "  git checkout main"
    exit 1
fi

success "On branch: $CURRENT_BRANCH"

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    error "Working directory has uncommitted changes"
    echo ""
    echo "Please commit or stash your changes before creating a release."
    exit 1
fi

# Check if we're up to date with remote
git fetch origin
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u} 2>/dev/null || echo "")

if [ -n "$REMOTE" ] && [ "$LOCAL" != "$REMOTE" ]; then
    warning "Local branch is not up to date with remote"
    echo ""
    echo "Please pull the latest changes:"
    echo "  git pull origin $CURRENT_BRANCH"
    exit 1
fi

# Get current version
CURRENT_VERSION=$(get_current_version)
info "Current version: $CURRENT_VERSION"

# Determine new version
if [[ "$BUMP_TYPE" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    # Specific version provided
    NEW_VERSION=$BUMP_TYPE
    validate_version "$NEW_VERSION"
    
    # Check if version is actually different
    if [ "$CURRENT_VERSION" == "$NEW_VERSION" ]; then
        error "New version ($NEW_VERSION) is the same as current version"
        exit 1
    fi
    
    # Check if version is less than current (not allowed)
    if [ "$(printf '%s\n' "$CURRENT_VERSION" "$NEW_VERSION" | sort -V | head -n1)" != "$CURRENT_VERSION" ]; then
        error "New version ($NEW_VERSION) is less than current version ($CURRENT_VERSION)"
        exit 1
    fi
else
    # Bump type provided
    case $BUMP_TYPE in
        patch|minor|major)
            NEW_VERSION=$(bump_version "$CURRENT_VERSION" "$BUMP_TYPE")
            ;;
        *)
            error "Invalid argument: $BUMP_TYPE"
            echo ""
            echo "Expected: patch, minor, major, or a version number (e.g., 0.2.0)"
            exit 1
            ;;
    esac
fi

info "New version: $NEW_VERSION"

# Check if tag already exists
TAG_NAME="v$NEW_VERSION"
if git rev-parse "$TAG_NAME" >/dev/null 2>&1; then
    error "Tag $TAG_NAME already exists"
    exit 1
fi

# Confirm before proceeding
echo ""
warning "This will:"
echo "  1. Update version in pyproject.toml to $NEW_VERSION"
echo "  2. Create a commit: 'Bump version to $NEW_VERSION'"
echo "  3. Create an annotated tag: $TAG_NAME"
echo "  4. Push to origin/$CURRENT_BRANCH"
echo "  5. Push tag $TAG_NAME (triggers GitHub release)"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    info "Release cancelled"
    exit 0
fi

# Update version
update_version "$NEW_VERSION"

# Create commit
info "Creating commit..."
git add "$PYPROJECT_FILE"
git commit -m "Bump version to $NEW_VERSION"
success "Created commit"

# Create annotated tag
info "Creating tag $TAG_NAME..."
git tag -a "$TAG_NAME" -m "Release $TAG_NAME"
success "Created tag $TAG_NAME"

# Push to remote
info "Pushing to origin/$CURRENT_BRANCH..."
git push origin "$CURRENT_BRANCH"
success "Pushed to origin/$CURRENT_BRANCH"

# Push tag (this triggers the GitHub Actions workflow)
info "Pushing tag $TAG_NAME..."
git push origin "$TAG_NAME"
success "Pushed tag $TAG_NAME"

echo ""
success "Release $TAG_NAME created successfully!"
echo ""
info "Next steps:"
echo "  1. GitHub Actions will automatically create the GitHub release"
echo "  2. Publish to PyPI: ./scripts/publish.sh pypi"
echo ""
info "View the release workflow:"
echo "  https://github.com/$(git config --get remote.origin.url | sed -E 's/.*github.com[:/](.*)\.git/\1/')/actions"
