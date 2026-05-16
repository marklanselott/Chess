#!/bin/bash
set -euo pipefail

case "$0" in
    */*) cd "${0%/*}" ;;
    *) cd "." ;;
esac

if [ -d ".venv" ]; then
    source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate
fi

python -m pytest -s tests "$@"
