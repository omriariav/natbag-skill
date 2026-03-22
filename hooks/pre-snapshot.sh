#!/bin/bash
# PreToolUse hook: injects snapshot context only for natbag skill calls.
# Daily snapshot itself runs via SessionStart hook (session-snapshot.sh).
set -euo pipefail

INPUT=$(cat)
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"

# Parse skill name from tool input (fallback to empty on any failure)
SKILL_NAME=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('skill', ''))
except:
    print('')
" 2>/dev/null || echo "")

# Only act on natbag skill calls
if [[ "$SKILL_NAME" != "natbag" && "$SKILL_NAME" != "natbag:natbag" ]]; then
    echo '{"decision":"approve"}'
    exit 0
fi

# Run snapshot (fast no-op if already ran today via SessionStart)
SNAPSHOT_OUTPUT=$(python3 "$PLUGIN_ROOT/skills/natbag/scripts/snapshot.py" 2>&1 || true)

SNAPSHOT_OUTPUT="$SNAPSHOT_OUTPUT" python3 -c "
import json, os
output = {
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'additionalContext': 'Natbag snapshot: ' + os.environ.get('SNAPSHOT_OUTPUT', '')
    }
}
print(json.dumps(output))
" || echo '{"decision":"approve"}'

exit 0
