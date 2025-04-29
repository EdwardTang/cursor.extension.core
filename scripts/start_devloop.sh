#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# start_devloop.sh - Launches the Oppie Dev-Loop components
# -----------------------------------------------------------------------------
# This script starts:
# 1. Codex Planner (using start_codex.sh) in a new terminal tab (macOS)
# 2. The Dev-Loop Watcher (watcher/watcher.py) in the current terminal
# -----------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

WATCHER_SCRIPT="$PROJECT_ROOT/watcher/watcher.py"
CODEX_LAUNCHER="$PROJECT_ROOT/start_codex.sh"

echo "🚀 Starting Oppie Dev-Loop..."

# 1. Start Codex Planner
echo "  -> Launching Codex Planner..."
if [[ ! -x "$CODEX_LAUNCHER" ]]; then
  echo "Error: Codex launcher script not found or not executable: $CODEX_LAUNCHER" >&2
  exit 1
fi
"$CODEX_LAUNCHER" # start_codex.sh handles launching in new terminal if needed

# Wait a moment for the terminal to potentially open
sleep 2

# 2. Start the Watcher
echo "  -> Launching Dev-Loop Watcher..."
if [[ ! -f "$WATCHER_SCRIPT" ]]; then
  echo "Error: Watcher script not found: $WATCHER_SCRIPT" >&2
  echo "Please ensure the watcher component is set up correctly." >&2
  exit 1
fi

# Execute the watcher in the current terminal
# Pass the codex launcher script path, as the watcher might need it for escalation
# (Adjust python command as needed for your environment)
exec python3 "$WATCHER_SCRIPT" "$CODEX_LAUNCHER"

echo "Watcher exited." 