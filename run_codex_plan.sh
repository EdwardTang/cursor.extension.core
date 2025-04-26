#!/usr/bin/env bash
set -eo pipefail

# 0. Find the latest plan request file and load its content
#    Strips newlines while preserving utf-8
SCRATCH=$(ls .scratchpad/*_plan_request.md | sort | tail -n 1)
if [[ -z "$SCRATCH" || ! -f "$SCRATCH" ]]; then
  echo "Error: No plan request file found in .scratchpad/" >&2
  exit 1
fi
PROMPT=$(awk 'BEGIN{ORS="";} {gsub(/\r/,""); print}' "$SCRATCH")


# 1. Run Codex inside a pseudo‑TTY so Ink UI stays intact
#    Use -qj for --quiet --json
# Print full command for troubleshooting
echo "Executing command: codex -qj -a full-auto -m o3 --project-doc \"$HOME/Projects/cloudkitchen/scratchpad.md\" with prompt from $SCRATCH"

script -q /dev/null \
  codex -qj -a full-auto -m o3 \
        --project-doc "$HOME/Projects/cloudkitchen/scratchpad.md" \
        "$PROMPT" |

# 2. Parse JSON‑Lines; join every assistant chunk into one block
#    Use try-catch for resilience against malformed JSON
jq -r 'try (
  select(.type=="message" and .role=="assistant")
  | .content[]?                                     # tolerate missing field
  | select(.type=="output_text")
  | .text
) catch ""' | tee codex_response.txt # Save response to file and print to stdout

# Exit with the exit code of the codex command (preserved by pipefail)
exit $? 