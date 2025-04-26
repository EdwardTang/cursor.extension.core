# Lessons

## User Specified Lessons

- Include info useful for debugging in the program output.
- Read the file before you try to edit it.
- Due to Cursor's limit, when you use `git` and `gh` and need to submit a multiline commit message, first write the message in a file, and then use `git commit -F <filename>` or similar command to commit. And then remove the file. Include "[Cursor] " in the commit message and PR title.

## Cursor learned

- For search results, ensure proper handling of different character encodings (UTF-8) for international queries
- Add debug information to stderr while keeping the main output clean in stdout for better pipeline integration
- When using seaborn styles in matplotlib, use 'seaborn-v0_8' instead of 'seaborn' as the style name due to recent seaborn version changes
- Use `chatgpt-4o-latest` as the model name for OpenAI. It is the latest GPT model and has vision capabilities as well. `o1` is the most advanced and expensive model from OpenAI. Use it when you need to do reasoning, planning, or get blocked.
- Use `claude-3.7-sonnet` as the model name for Claude. It is the latest Claude model and has vision capabilities as well.
- When encountering unexpected execution behavior (like hangs or wrong logic) with build tools (e.g., `./gradlew run`), double-check the build configuration file (e.g., `build.gradle`) for the correct entry point (`mainClass`) setting, as temporary changes or misconfigurations can lead to running unintended code.
- o3 and o4-mini are the most advanced models from OpenAI. Avoid using them for coding for now due to severe hallucinations. 


# Multi-Agent Scratchpad

## Background and Motivation

(Planner writes: User/business requirements, macro objectives, why this problem needs to be solved)


## Key Challenges and Analysis


## Verifiable Success Criteria

## High-level Task Breakdown


## Current Status / Progress Tracking
