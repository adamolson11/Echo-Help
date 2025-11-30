#!/usr/bin/env bash
echo "=== IRON SAFETY CHECK ==="
echo ""
echo "Branch:"
git branch --show-current
echo ""
echo "Git Status:"
git status --short
echo ""
echo "Last 5 commits:"
git --no-pager log --oneline -5
echo ""
echo "Search.tsx changes:"
git status --short frontend/src/Search.tsx
