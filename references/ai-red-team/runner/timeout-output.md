# Timeout output handling

The runner waits up to one hour for each automated subprocess. On POSIX systems,
`run_cmd` starts each command in a new session. If it times out, the runner sends
SIGKILL to that command's process group, then drains output and reaps the child
within bounded cleanup intervals. It records exit code 124 and keeps captured
stdout and stderr in the corresponding phase log, followed by a
`timeout: <command>` marker. Captured streams are appended in the same order used
for completed commands. Python may expose timeout output as bytes even when text
mode was requested; invalid UTF-8 bytes are displayed with replacement
characters. If group signalling or output draining cannot be confirmed, the
phase log includes a `timeout cleanup incomplete` diagnostic.

On non-POSIX systems, cleanup can stop only the immediate child. The runner
cannot promise process-tree termination or bounded pipe draining there, and
descendants that outlive the child may keep output pipes open. Deliberately
detached descendants and work started outside the command's process group are
outside the POSIX timeout guarantee. The workflow verifies the synthetic
process-group behavior on Ubuntu and macOS; it does not test scanners, models,
providers, or targets.

Phase and Promptfoo command logs still pass through the runner's existing limited
token scrub before they are written. Raw garak hitlogs remain separate, unchanged
evidence and may contain sensitive content. Treat the complete engagement
directory as sensitive. The offline timeout fixtures exercise the command helper
and report path without running a scanner, model, or target.

Contributed by Ryan Wentzel | [ryanwentzel.me](https://ryanwentzel.me).
