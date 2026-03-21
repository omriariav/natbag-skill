#!/bin/bash
# Pre-tool hook: runs daily snapshot when natbag skill is invoked.
# Fires on PreToolUse(Skill) — checks if the skill is "natbag" before running.
set -euo pipefail

INPUT=$(cat)
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"

# Parse skill name from tool input — only act on natbag
SKILL_NAME=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('skill', ''))
except:
    print('')
" 2>/dev/null)

if [[ "$SKILL_NAME" != *"natbag"* ]]; then
    exit 0
fi

# Run snapshot (self-guards to once daily)
SNAPSHOT_OUTPUT=$(python3 "$PLUGIN_ROOT/skills/natbag/scripts/snapshot.py" 2>&1 || true)

# Return context to Claude — pass output via env var to avoid shell/Python injection
SNAPSHOT_OUTPUT="$SNAPSHOT_OUTPUT" python3 -c "
import json, os
output = {
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'additionalContext': 'Natbag snapshot: ' + os.environ.get('SNAPSHOT_OUTPUT', '')
    }
}
print(json.dumps(output))
"

exit 0
