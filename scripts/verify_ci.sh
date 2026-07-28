#!/usr/bin/env bash
# verify_ci.sh - Automatically reproduces the GitHub Actions Ubuntu CI environment locally via Docker
# and runs full lesson conversion & diagram rendering verification before pushing.

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==================================================================="
echo " 🐋 [1/3] Checking Docker Daemon connection..."
echo "==================================================================="
if ! docker info >/dev/null 2>&1; then
    echo "❌ ERROR: Cannot connect to Docker daemon."
    echo "👉 Please open Docker Desktop or start Colima/OrbStack on your host machine to run Linux CI parity checks."
    exit 1
fi
echo "✅ Docker is running."

echo ""
echo "==================================================================="
echo " 🛠️  [2/3] Building Linux CI Parity Container (Ubuntu 22.04, Node 20, Pandoc, Chromium)..."
echo "==================================================================="
docker build -t notification-ci:latest -f Dockerfile.ci .
echo "✅ CI container build complete."

echo ""
echo "==================================================================="
echo " 🧪 [3/3] Executing verification suite inside Linux CI container..."
echo "==================================================================="
echo "--> Test 1: Verifying EPUB generation and Mermaid diagram rendering (test_email.py --dry-run)"
docker run --rm -v "$REPO_ROOT:/workspace" -w /workspace notification-ci:latest python3 scripts/test_email.py --dry-run

echo ""
echo "--> Test 2: Verifying course state and next lesson EPUB conversion (send_to_kindle.py --dry-run)"
docker run --rm -v "$REPO_ROOT:/workspace" -w /workspace notification-ci:latest python3 scripts/send_to_kindle.py --dry-run

echo ""
echo "🎉 ALL CI VERIFICATION TESTS PASSED! Your environment parity is guaranteed and ready for GitHub Actions."
