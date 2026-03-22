#!/bin/bash
# SessionStart hook: runs daily flight snapshot (self-guards to once/day in snapshot.py).
# Runs at session start so flight data is fresh without blocking Skill calls.
set -euo pipefail

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"

python3 "$PLUGIN_ROOT/skills/natbag/scripts/snapshot.py" > /dev/null 2>&1 || true

exit 0
