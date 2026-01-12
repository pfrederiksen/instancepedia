#!/bin/bash
# Setup git hooks for instancepedia development
# Run this after cloning the repository

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

echo "Setting up git hooks for instancepedia..."

# Create pre-push hook
cat > "$HOOKS_DIR/pre-push" << 'EOF'
#!/bin/bash
# Pre-push hook to prevent direct pushes to main/master

protected_branches="main master"
current_branch=$(git symbolic-ref HEAD | sed -e 's,.*/\(.*\),\1,')

for branch in $protected_branches; do
    if [ "$current_branch" = "$branch" ]; then
        echo "❌ ERROR: Direct push to '$branch' is not allowed!"
        echo ""
        echo "This project requires pull requests for all changes to $branch."
        echo ""
        echo "Correct workflow:"
        echo "  1. git checkout -b feature/your-feature-name"
        echo "  2. git add . && git commit -m 'your message'"
        echo "  3. git push -u origin feature/your-feature-name"
        echo "  4. gh pr create --title '...' --body '...'"
        echo "  5. gh pr merge --squash --delete-branch"
        echo ""
        echo "To bypass this check (NOT RECOMMENDED):"
        echo "  git push --no-verify"
        echo ""
        exit 1
    fi
done

exit 0
EOF

# Make hooks executable
chmod +x "$HOOKS_DIR/pre-push"

echo "✅ Git hooks installed successfully!"
echo ""
echo "Installed hooks:"
echo "  - pre-push: Prevents direct pushes to main/master"
echo ""
echo "You're all set! Remember: Always use feature branches and PRs."
