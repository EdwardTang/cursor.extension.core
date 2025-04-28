#!/usr/bin/env bash
set -eo pipefail

# 0. Find the latest plan request file (ending with _plan_request.md) and load its content
#    Strips newlines while preserving utf-8
LATEST_PLAN_REQUEST=$(ls -t .scratchpad_logs/*_plan_request.md 2>/dev/null | head -n 1)
if [[ -z "$LATEST_PLAN_REQUEST" || ! -f "$LATEST_PLAN_REQUEST" ]]; then
  echo "Error: No plan request file (*_plan_request.md) found in .scratchpad_logs/" >&2
  exit 1
fi
PROMPT=$(awk 'BEGIN{ORS="";} {gsub(/\r/,""); print}' "$LATEST_PLAN_REQUEST")

# Define project root - automatically detect it based on script location
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Define temporary file for raw output
TEMP_OUTPUT_FILE=$(mktemp)

# Ensure temporary file is cleaned up on exit
trap 'rm -f -- "$TEMP_OUTPUT_FILE"' EXIT

# 1. Run Codex inside a pseudo‑TTY so Ink UI stays intact
#    Use -qj for --quiet --json
# Print full command for troubleshooting
echo "Executing command: codex -qj -a full-auto -m o3 --project-doc \"$PROJECT_ROOT/scratchpad.md\" with prompt from $LATEST_PLAN_REQUEST"

# Run codex and save the RAW output to the temporary file
script -q /dev/null codex -qj -a full-auto -m o3 \
        --project-doc "$PROJECT_ROOT/scratchpad.md" \
        "$PROMPT" > "$TEMP_OUTPUT_FILE" # Redirect raw output to temp file

CODEX_EXIT_CODE=$?

# Capture timestamp AFTER generating the plan response
TIMESTAMP=$(date +"%Y-%m-%dT%H_%M_%S")

# Define final output filename with timestamp
SCRATCHPAD_PLAN_RESPONSE=".scratchpad_logs/${TIMESTAMP}_plan_response.md"

# Copy the raw output from temp file to the final timestamped file
cp "$TEMP_OUTPUT_FILE" "$SCRATCHPAD_PLAN_RESPONSE"

# Output information about the saved response
echo "--------------------------------------------------"
echo "✅ Planner's raw response saved to: $SCRATCHPAD_PLAN_RESPONSE"
echo ""
echo "➡️ Next step: Executor, please manually extract the actionable plan" 
echo "   (sections like '## Key Challenges', '## Next Steps', etc.)" 
echo "   from the raw JSON/Markdown mix in the file above."
echo "--------------------------------------------------"

# Exit with the exit code of the codex command
exit $CODEX_EXIT_CODE 