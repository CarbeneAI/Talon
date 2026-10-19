# Timeout output handling

The runner waits up to one hour for each automated subprocess. If a command
times out, `run_cmd` records exit code 124 and keeps any captured stdout and
stderr in the corresponding phase log, followed by a `timeout: <command>` marker.
Captured streams are appended in the same order used for completed commands.
Python may expose timeout output as bytes even when text mode was requested;
invalid UTF-8 bytes are displayed with replacement characters.

Phase and Promptfoo command logs still pass through the runner's existing limited
token scrub before they are written. Raw garak hitlogs remain separate, unchanged
evidence and may contain sensitive content. Treat the complete engagement
directory as sensitive. The offline timeout fixtures exercise the command helper
and report path without running a scanner, model, or target.

Contributed by Ryan Wentzel | [ryanwentzel.me](https://ryanwentzel.me).
