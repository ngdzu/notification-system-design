#!/usr/bin/env bash
# install_git_hooks.sh - Installs verify_ci.sh as a Git pre-push hook so builds are automatically
# verified against the Linux CI container before pushing to GitHub.

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOK_DIR="$REPO_ROOT/.git/hooks"
PRE_PUSH_HOOK="$HOOK_DIR/pre-push"

echo "Installing pre-push hook to $PRE_PUSH_HOOK..."
mkdir -p "$HOOK_DIR"

cat << 'EOF' > "$PRE_PUSH_HOOK"
#!/usr/bin/env bash
echo "=== 🔒 Git Pre-Push Hook: Running Automated CI Environment Parity Check ==="
exec ./scripts/verify_ci.sh
EOF

chmod +x "$PRE_PUSH_HOOK"
echo "✅ SUCCESS: Git pre-push hook installed! Every 'git push' will now automatically verify in the CI Docker container first."
