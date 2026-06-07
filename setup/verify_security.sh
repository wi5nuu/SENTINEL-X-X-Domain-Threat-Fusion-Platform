#!/bin/bash
# Security Verification Script - Check for exposed sensitive files

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "SECURITY VERIFICATION"
echo "=========================================="
echo ""

ISSUES_FOUND=0

# Check for sensitive files in git
echo "[1/6] Checking for sensitive files in git tracking..."

SENSITIVE_IN_GIT=$(git ls-files | grep -E '\.(env|license|key|pem|pfx|cert|encrypted|enc)$' | grep -v '.env.example')

if [ -n "$SENSITIVE_IN_GIT" ]; then
    echo -e "${RED}✗ CRITICAL: Sensitive files are tracked in git!${NC}"
    echo "$SENSITIVE_IN_GIT"
    echo ""
    echo "Remove with: git rm --cached <file>"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo -e "${GREEN}✓ No sensitive files in git tracking${NC}"
fi

# Check for proprietary files that should not exist in public repo
echo ""
echo "[2/6] Checking for proprietary files..."

PROPRIETARY_FILES=(
    "src/common/license_manager.py"
    "src/common/hardware_fingerprint.py"
    "src/common/crypto_vault.py"
    "src/common/activation_service.py"
    "setup/generate_license.py"
    "setup/install_private.sh"
)

FOUND_PROPRIETARY=0
for file in "${PROPRIETARY_FILES[@]}"; do
    if [ -f "$file" ] && git ls-files --error-unmatch "$file" 2>/dev/null; then
        echo -e "${RED}✗ Proprietary file in git: $file${NC}"
        FOUND_PROPRIETARY=$((FOUND_PROPRIETARY + 1))
    fi
done

if [ $FOUND_PROPRIETARY -eq 0 ]; then
    echo -e "${GREEN}✓ No proprietary files in git${NC}"
else
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# Check for license/activation files
echo ""
echo "[3/6] Checking for license/activation files..."

LICENSE_FILES=$(find . -name ".license" -o -name "*.license" -o -name ".machine_id" -o -name "activation.dat" | grep -v ".git")

if [ -n "$LICENSE_FILES" ]; then
    echo -e "${YELLOW}⚠ License/activation files found locally (OK if not in git):${NC}"
    echo "$LICENSE_FILES"
    
    # Check if any are in git
    for file in $LICENSE_FILES; do
        if git ls-files --error-unmatch "$file" 2>/dev/null; then
            echo -e "${RED}✗ CRITICAL: License file is tracked in git: $file${NC}"
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        fi
    done
else
    echo -e "${GREEN}✓ No license files found${NC}"
fi

# Check for credentials in files
echo ""
echo "[4/6] Scanning for exposed credentials in code..."

CREDENTIAL_PATTERNS=(
    "password\s*=\s*['\"][^'\"]{8,}['\"]"
    "api_key\s*=\s*['\"][a-zA-Z0-9]{20,}['\"]"
    "secret\s*=\s*['\"][a-zA-Z0-9]{20,}['\"]"
    "token\s*=\s*['\"][a-zA-Z0-9]{20,}['\"]"
)

CRED_FOUND=0
for pattern in "${CREDENTIAL_PATTERNS[@]}"; do
    MATCHES=$(grep -rniE "$pattern" src/ 2>/dev/null | grep -v ".pyc" | grep -v "__pycache__" | grep -v ".example" | head -5)
    if [ -n "$MATCHES" ]; then
        echo -e "${RED}✗ Potential credentials found:${NC}"
        echo "$MATCHES"
        CRED_FOUND=$((CRED_FOUND + 1))
    fi
done

if [ $CRED_FOUND -eq 0 ]; then
    echo -e "${GREEN}✓ No hardcoded credentials detected${NC}"
else
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# Check .gitignore coverage
echo ""
echo "[5/6] Verifying .gitignore coverage..."

SHOULD_BE_IGNORED=(
    ".env"
    ".license"
    ".machine_id"
    "secrets/"
    "credentials/"
    "private_keys/"
)

GITIGNORE_ISSUES=0
for item in "${SHOULD_BE_IGNORED[@]}"; do
    if ! grep -q "$item" .gitignore 2>/dev/null; then
        echo -e "${RED}✗ Missing in .gitignore: $item${NC}"
        GITIGNORE_ISSUES=$((GITIGNORE_ISSUES + 1))
    fi
done

if [ $GITIGNORE_ISSUES -eq 0 ]; then
    echo -e "${GREEN}✓ .gitignore properly configured${NC}"
else
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# Check git hooks
echo ""
echo "[6/6] Verifying git hooks are installed..."

if [ ! -f ".git/hooks/pre-commit" ]; then
    echo -e "${YELLOW}⚠ Pre-commit hook not installed${NC}"
    echo "Run: bash setup/setup_git_hooks.sh"
elif [ ! -x ".git/hooks/pre-commit" ]; then
    echo -e "${YELLOW}⚠ Pre-commit hook not executable${NC}"
    echo "Run: chmod +x .git/hooks/pre-commit"
else
    echo -e "${GREEN}✓ Pre-commit hook installed${NC}"
fi

if [ ! -f ".git/hooks/pre-push" ]; then
    echo -e "${YELLOW}⚠ Pre-push hook not installed${NC}"
    echo "Run: bash setup/setup_git_hooks.sh"
else
    echo -e "${GREEN}✓ Pre-push hook installed${NC}"
fi

# Summary
echo ""
echo "=========================================="
if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}SECURITY CHECK PASSED${NC}"
    echo "No critical issues found."
else
    echo -e "${RED}SECURITY ISSUES FOUND: $ISSUES_FOUND${NC}"
    echo "Please fix issues above before committing/pushing."
    exit 1
fi
echo "=========================================="

exit 0
