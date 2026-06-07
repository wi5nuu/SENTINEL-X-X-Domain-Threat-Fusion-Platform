#!/bin/bash
# Setup Git Hooks for Security

echo "Setting up Git security hooks..."

# Create hooks directory if not exists
mkdir -p .git/hooks

# Copy pre-commit hook
cp .git-hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Create pre-push hook
cat > .git/hooks/pre-push << 'EOF'
#!/bin/bash
# Pre-push hook to prevent sensitive data push

echo "Running pre-push security checks..."

# Check if any sensitive files are tracked
SENSITIVE_FILES=$(git ls-files | grep -E '\.(env|license|key|pem|pfx|cert)$')

if [ -n "$SENSITIVE_FILES" ]; then
    echo "ERROR: Tracked sensitive files detected!"
    echo "$SENSITIVE_FILES"
    echo ""
    echo "Remove these files from git tracking:"
    echo "  git rm --cached <file>"
    exit 1
fi

# Check for large files (potential data leaks)
LARGE_FILES=$(git diff --cached --name-only | xargs -I {} sh -c 'if [ -f "{}" ]; then du -k "{}" | awk '"'"'$1 > 10000 {print $2}'"'"'; fi')

if [ -n "$LARGE_FILES" ]; then
    echo "WARNING: Large files detected (>10MB):"
    echo "$LARGE_FILES"
    echo ""
    read -p "Continue push? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "✓ Pre-push checks passed"
exit 0
EOF

chmod +x .git/hooks/pre-push

# Create commit-msg hook for commit message validation
cat > .git/hooks/commit-msg << 'EOF'
#!/bin/bash
# Commit message hook

COMMIT_MSG_FILE=$1
COMMIT_MSG=$(cat "$COMMIT_MSG_FILE")

# Check for accidental credential mentions
if echo "$COMMIT_MSG" | grep -qiE "(password|api.?key|secret|token|credential)"; then
    echo "WARNING: Commit message mentions sensitive terms"
    echo "Make sure you're not exposing credentials in commit message"
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

exit 0
EOF

chmod +x .git/hooks/commit-msg

echo "✓ Git hooks installed successfully"
echo ""
echo "Installed hooks:"
echo "  - pre-commit: Prevents committing sensitive files"
echo "  - pre-push: Additional checks before pushing"
echo "  - commit-msg: Validates commit messages"
