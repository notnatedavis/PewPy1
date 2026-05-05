#!/usr/bin/env bash
# clean_pycache.sh – Recursively delete all __pycache__ folders from project root

set -euo pipefail

# Determine project root (directory where this script lives, or use pwd)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Searching from: $SCRIPT_DIR"
echo

CACHE_DIRS=$(find . -type d -name '__pycache__' -print)

if [ -z "$CACHE_DIRS" ]; then
    echo "No __pycache__ directories found under $SCRIPT_DIR"
    echo "(They only exist after Python runs your modules.)"
    exit 0
fi

echo "Found:"
echo "$CACHE_DIRS"
echo

read -p "Delete all listed directories? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "$CACHE_DIRS" | xargs rm -rf
    echo "Done. All __pycache__ folders removed."
else
    echo "Cancelled."
fi