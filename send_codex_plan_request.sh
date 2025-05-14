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

# 1. Run Open-Codex inside a pseudo‑TTY so Ink UI stays intact
#    Use -qj for --quiet --json
# Print full command for troubleshooting
echo "Executing command: codex -qj -a full-auto --provider gemini -m gemini-2.5-pro-preview-05-06 --notify --debug --project-doc \"$PROJECT_ROOT/scratchpad.md\" with prompt from $LATEST_PLAN_REQUEST"

# Run open-codex and save the RAW output to the temporary file

# Define parts of the command for logging purposes
CODEX_EXECUTABLE="codex"
CODEX_FLAGS="-qj -a full-auto --provider gemini -m gemini-2.5-pro-preview-05-06 --notify --debug"
# Ensure arguments with spaces are quoted for the loggable command string
CODEX_PROJECT_DOC_ARG="--project-doc \"$PROJECT_ROOT/scratchpad.md\""
CODEX_PROMPT_ARG="\"$PROMPT\""
LOGGABLE_CODEX_COMMAND="$CODEX_EXECUTABLE $CODEX_FLAGS $CODEX_PROJECT_DOC_ARG $CODEX_PROMPT_ARG"

TEMP_OUTPUT_FILE=$(mktemp)
if [ -z "$TEMP_OUTPUT_FILE" ]; then
    echo "❌ ERROR: Failed to create temporary file. Exiting." >&2
    exit 1
fi

# Execute the codex command, redirecting both stdout and stderr to the temporary file
# This ensures all output from codex, including errors, is captured.
script -q /dev/null $CODEX_EXECUTABLE $CODEX_FLAGS \
        --project-doc "$PROJECT_ROOT/scratchpad.md" \
        "$PROMPT" > "$TEMP_OUTPUT_FILE" 2>&1

CODEX_EXIT_CODE=$?

# Capture timestamp AFTER trying to generate the plan response
TIMESTAMP=$(date +"%Y-%m-%dT%H_%M_%S")

if [ $CODEX_EXIT_CODE -ne 0 ]; then
    # Planner failed
    ERROR_LOG_FILE=".scratchpad_logs/${TIMESTAMP}_plan_error.md"
    
    CYCLE_INFO="Cycle Number: Not determined (extraction not implemented in this version)"
    # Attempt to extract Cycle Number from PROMPT if possible and if PROMPT exists and is readable
    if [ -f "$LATEST_PLAN_REQUEST" ] && [ -r "$LATEST_PLAN_REQUEST" ]; then
        CYCLE_NUMBER_LINE=$(grep -i "CYCLE_NUMBER=" "$LATEST_PLAN_REQUEST" | head -n 1)
        if [ -n "$CYCLE_NUMBER_LINE" ]; then
            # Extract value after '=', remove leading/trailing whitespace
            CYCLE_VALUE=$(echo "$CYCLE_NUMBER_LINE" | cut -d'=' -f2- | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            CYCLE_INFO="Cycle Number: $CYCLE_VALUE (from $LATEST_PLAN_REQUEST)"
        else
            CYCLE_INFO="Cycle Number: Field not found in $LATEST_PLAN_REQUEST"
        fi
    else
        CYCLE_INFO="Cycle Number: Prompt file $LATEST_PLAN_REQUEST not found or not readable."
    fi

    # Construct error message
    ERROR_MESSAGE=$(cat <<EOF
--------------------------------------------------
❌ ERROR: Planner (codex command) failed!
--------------------------------------------------

$CYCLE_INFO
Prompt File Used: $LATEST_PLAN_REQUEST
Attempted Command: $LOGGABLE_CODEX_COMMAND
Exit Code: $CODEX_EXIT_CODE
Timestamp: $TIMESTAMP

Possible Causes & Troubleshooting Steps:
1.  Review Planner\'s Output/Error below: 
    The raw output/error from the 'codex' command is captured in '$TEMP_OUTPUT_FILE' (and will be shown below if not empty). Inspect it for specific error messages from 'codex' or the LLM.
2.  Prompt File Issues ('$LATEST_PLAN_REQUEST'):
    - Verify the existence, readability, and content of the prompt file.
    - Ensure it adheres to the expected Template A format (refer to '@drop-in_template_A.mdc' or relevant design documents).
    - Check for syntax errors, missing required fields, or incorrect values.
3.  Codex Tool / LLM (gemini-2.5-pro-preview-05-06) Issues:
    - Consult 'codex' tool documentation for specific exit code meanings if available.
    - Possible API key misconfiguration, authentication problems, or rate limits with the underlying LLM.
    - The LLM might be temporarily unavailable or experiencing internal issues.
4.  Network Connectivity:
    - Ensure the machine has stable internet access.
    - Verify that the system can reach the 'codex' service and associated LLM endpoints (check firewalls, proxies).
5.  Resource Issues:
    - Check for sufficient disk space, memory, or other system resource limitations that might affect 'codex' execution.
6.  Script Arguments or Environment:
    - Ensure PROJECT_ROOT ('$PROJECT_ROOT') is correctly set and points to a valid directory.
    - Verify that the '$PROMPT' variable correctly points to the intended prompt file.

Guidance for Executor (Cursor Composer / User):
-   **Analyze:** Carefully review this error message and the captured output from '$TEMP_OUTPUT_FILE' (pasted below if available).
-   **Retry:** If the error seems transient (e.g., temporary network glitch, LLM unavailability), re-running 'send_codex_plan_request.sh' with the *same* prompt file ('$LATEST_PLAN_REQUEST') might resolve it.
-   **Revise Prompt:** If the prompt file ('$LATEST_PLAN_REQUEST') or its content appears to be the cause, correct it, then re-run 'send_codex_plan_request.sh'.
-   **Update Scratchpad:** Document this failure (including this error log path: '$ERROR_LOG_FILE'), the attempted prompt ('$LATEST_PLAN_REQUEST'), the exit code ($CODEX_EXIT_CODE), and key findings in the 'Multi-Agent Scratchpad' section of '$PROJECT_ROOT/scratchpad.md'.
-   **Next Action:** 
    - If you can identify and fix the cause (e.g., correcting the prompt file), proceed with the corrected approach.
    - If the issue is persistent, unclear, or relates to external services, after documenting in scratchpad.md, escalate to the Human Supervisor for guidance, providing them with this error log.

This error occurred while trying to generate a plan response.
The raw output from the attempt (stdout & stderr) is in: $TEMP_OUTPUT_FILE
No successful plan response was saved to '.scratchpad_logs/'. This error report has been saved to: $ERROR_LOG_FILE
--------------------------------------------------
EOF
)
    echo "$ERROR_MESSAGE" > "$ERROR_LOG_FILE" # Save detailed error to its own log file
    echo "$ERROR_MESSAGE" # Also print to stdout for immediate visibility
    
    if [ -s "$TEMP_OUTPUT_FILE" ]; then
        echo "" # Add a blank line for separation
        echo "--- Captured output from codex command (from $TEMP_OUTPUT_FILE): ---"
        cat "$TEMP_OUTPUT_FILE"
        echo "--- End of captured output ---"
    else
        echo "--- Temporary output file ($TEMP_OUTPUT_FILE) is empty. ---"
    fi
    
    rm -f "$TEMP_OUTPUT_FILE" # Clean up temp file
    exit $CODEX_EXIT_CODE # Exit with the original error code from codex
else
    # Planner succeeded
    SCRATCHPAD_PLAN_RESPONSE=".scratchpad_logs/${TIMESTAMP}_plan_response.md"

    # Copy the raw output from temp file to the final timestamped file
    # This now contains both stdout and stderr from codex
    cp "$TEMP_OUTPUT_FILE" "$SCRATCHPAD_PLAN_RESPONSE"

    # Output information about the saved response
    echo "--------------------------------------------------"
    echo "✅ Planner's raw response (stdout & stderr) saved to: $SCRATCHPAD_PLAN_RESPONSE"
    echo ""
    echo "➡️ Next step: Executor, please manually extract the actionable plan" 
    echo "   (sections like '## Key Challenges', '## Next Steps', etc.)"
    echo "   from the raw JSON/Markdown mix in the file above."
    echo "   Note: The file now contains both stdout and stderr from the planner."
    echo "--------------------------------------------------"
    
    rm -f "$TEMP_OUTPUT_FILE" # Clean up temp file
    exit 0 # Explicitly exit 0 on success
fi