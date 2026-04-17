#!/bin/bash
# Development quality checks: format, lint, test

set -e

TARGET="${1:-backend/}"

echo "==> Formatting with black..."
uv run black "$TARGET"

echo "==> Sorting imports with isort..."
uv run isort "$TARGET"

echo "==> Linting with flake8..."
uv run flake8 "$TARGET" --max-line-length=88 --extend-ignore=E203,W503

echo "==> Running tests..."
cd backend && uv run pytest tests/ -q

echo ""
echo "All checks passed."
