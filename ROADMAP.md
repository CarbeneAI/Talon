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
- All interpolated report fields are escaped as literal text, including URL
  punctuation to prevent autolinks. Field line breaks become spaces; the
  template keeps its headings and table. Real GFM rendering fixtures with HTML
  and autolinking enabled cover metadata, evidence, filenames, and phase notes.
- Requested automated command failures, missing tools, and missing configured
  promptfoo files are reported separately from manual guidance. The report is
  preserved before the runner returns status 1; status 0 is not a clean assessment.
- Default `engagements/` output at any depth in the checkout, the copied
  runner config, and root `.mcp.json` are ignored. Temporary Git repositories
  verify those rules while keeping examples and fixtures outside `engagements/` trackable. Custom
  locations and already tracked files still require explicit handling.
- Unsupported endpoint and key-variable config options fail before output is
  created or tools run. The supported `openai` type requires an empty endpoint
  and `OPENAI_API_KEY`; ambient provider environment behavior remains separate.
- Hitlog parsing uses strict UTF-8 physical lines and diagnoses corrupt JSON,
  non-object records, and read failures without exposing rejected payloads or
  exception text. Valid rows and raw bytes are preserved, including structured
  prompt/output values through the existing string rendering. Parsing issues
  have a separate report count/section and cause status 1 after report writing.
  Missing/empty hitlogs remain explicitly inconclusive without a parse failure.
- Thirty offline tests cover report redaction, truncation, ordinary formatting,
  raw evidence preservation, mocked execution status, configuration rejection,
  Git ignore rules, inert evidence rendering, physical JSONL boundaries, fixed
  parsing diagnostics, read failures, and structured/legacy extraction. The
  [CI job](.github/workflows/runner-tests.yml) runs them with Python 3.12 and
  the pinned offline `requirements-test.txt` dependencies. This does not validate
  scanners, live services, SSH MCP, or every Markdown viewer.
- Setup documentation identifies the SSH MCP example as a provider-dependent
  template. No default provider is selected or validated. Runner phases 1, 5,
  and 6 print manual guidance rather than execute those phases.

## Proposed next steps

### 1. Harden report redaction and evidence parsing

Review the supported token patterns and report fields before changing them.
The baseline now covers malformed/non-object JSONL records, UTF-8 and physical
line boundaries, read failures, alternate field names, structured values, empty
and absent hitlogs, and token boundaries. Keep those contracts when refining
redaction or evaluating a future version-specific structured-message adapter.

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

Default output and local configuration ignore rules are now covered by offline
fixtures. Review custom output paths, existing tracked evidence, temporary files,
and ambient provider environment settings before release. The supported
`openai` command reads `OPENAI_API_KEY` directly. Configuration now rejects
nonempty `target.endpoint` and custom `target.api_key_env` values because those
options are not mapped to garak. Custom endpoint routing and key-variable
mapping remain unsupported; validation does not constrain every provider
environment setting or establish endpoint authenticity.

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
