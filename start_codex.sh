#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# start_codex.sh — Convenience launcher for Codex Planner )
# -----------------------------------------------------------------------------
# This script opens a new zsh session and executes the Codex command recommended
# by the tech-stack documentation:
#     codex --notify --debug
#
# Usage:
#   ./start_codex.sh [extra_codex_args]
#
# Examples:
#   ./start_codex.sh
#   ./start_codex.sh --project-doc scratchpad.md
#
# If run on macOS, the script will attempt to spawn a new Terminal tab/window
# to keep the Codex UI separate from your current shell. On other platforms it
# simply runs the command in the current terminal.
# -----------------------------------------------------------------------------
set -euo pipefail

DEFAULT_CMD=(codex --notify --debug --project-doc scratchpad.md)
CMD=("${DEFAULT_CMD[@]}" "$@")

launch_in_macos_terminal() {
  local joined
  # Join arguments into a single string with proper escaping for AppleScript
  joined="$(printf ' %q' "${CMD[@]}")"

  # shellcheck disable=SC2155
  local osa_script="tell application \"Terminal\"\n  do script \"zsh -lc 'set -e; ${joined:1}'\"\n  activate\nend tell"
  osascript -e "$osa_script" 2>/dev/null || {
    echo "⚠️  Failed to open macOS Terminal. Falling back to current shell." >&2
    return 1
  }
  echo "🚀 Codex started in a new Terminal window."
}

main() {
  case "$(uname -s)" in
    Darwin)
      # On macOS, prefer a separate Terminal window for better UX
      launch_in_macos_terminal || zsh -lc "${CMD[*]}"
      ;;
    *)
      # Other OS: run directly in the current shell
      echo "🚀 Running Codex in current shell. Press Ctrl+C to stop."
      exec zsh -lc "${CMD[*]}"
      ;;
  esac
}

main "$@" 