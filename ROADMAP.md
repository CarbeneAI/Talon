# Proposed roadmap

This is a contributor proposal for maintainer discussion, not an adopted plan,
commitment, or timeline. Priorities below focus on report reliability, setup
accuracy, and safe handling of engagement data. They do not propose additional
scanning or attack capabilities.

## Current baseline

- The runner redacts its existing token patterns from generated findings reports,
  including metadata and phase notes, and scrubs hitlog text before truncation.
  Raw evidence remains unchanged and sensitive. Redaction is not comprehensive
  secret detection.
- Four synthetic, offline regression tests cover report redaction, truncation,
  ordinary formatting, and raw evidence preservation. The
  [CI job](.github/workflows/runner-tests.yml) runs them with Python 3.12 and
  PyYAML 6.0.3. This does not validate scanners, live services, or SSH MCP.
- Setup documentation identifies the SSH MCP example as a provider-dependent
  template. No default provider is selected or validated. Runner phases 1, 5,
  and 6 print manual guidance rather than execute those phases.

## Proposed next steps

### 1. Harden report redaction and evidence parsing

Review the supported token patterns and report fields before changing them.
Add deterministic synthetic fixtures for malformed or non-object JSONL records,
alternate field names, empty hitlogs, absent hitlogs, and token boundaries.

Acceptance criteria:
- Malformed or unsupported records produce the documented warning or error and
  are not presented as proof of a clean run.
- Tests exercise every report field that can contain evidence or metadata and
  distinguish supported redaction from documented limitations.
- Fixtures confirm raw files remain byte-for-byte unchanged and ordinary
  evidence remains useful.
- Expected output checks control timestamps and file ordering so failures are
  reproducible. Tests run offline with the minimal CI dependency set.

### 2. Resolve the SSH provider decision and validate its contract

Maintainers decide whether to document a reviewed provider or retain a
bring-your-own-provider workflow. Record the choice and its validation limits.

Acceptance criteria:
- Documentation specifies the selected provider's reviewed version, runtime,
  launch command, authentication settings, and configuration scope, or explicitly
  retains the template and explains what users must supply.
- If a provider is selected, local mock contract checks validate configuration,
  advertised tool schemas, and failure handling without contacting a VM or target.
- Mock checks are labeled as such. Any live compatibility claim is supported by
  a separate, authorized validation record, not inferred from passing mocks.

### 3. Clarify configuration and engagement data handling

Review where the runner writes reports, logs, raw evidence, and temporary files,
and how those paths interact with repository ignore rules.

Acceptance criteria:
- Synthetic checks verify the documented environment-variable key handling and
  identify any sensitive data written by the runner, including failure paths.
- Default output and real configuration paths are either ignored or clearly
  documented with an explicit safe storage procedure.
- Documentation explains access, retention, disposal, and report-sharing review
  without promising that redaction removes every secret.

### 4. Detect documentation drift in CI

Extend lightweight offline checks alongside the existing report tests.

Acceptance criteria:
- Relative documentation links resolve, example JSON parses, and maintained
  shell scripts pass syntax checks without executing them.
- Runner phase and supported-target descriptions are checked against the current
  implementation or covered by an explicit review checklist.
- README test commands match CI dependencies and working directories. CI labels
  distinguish static, fixture, mock, and any separately authorized live checks.
