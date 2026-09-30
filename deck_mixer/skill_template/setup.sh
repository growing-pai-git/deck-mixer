#!/usr/bin/env bash
# Installs pandoro into a local .venv next to this script. Safe to re-run.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

if [ ! -d .venv ]; then
    python3 -m venv .venv
fi

.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install ./vendor/pandoro-src -q

echo "pandoro installed. Run: .venv/bin/pandoro deck-mixer --help"
