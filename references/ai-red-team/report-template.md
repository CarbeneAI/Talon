# AI / LLM Red-Team Assessment Report

**Client:** <client>
**System under test:** <model + application>
**Engagement window:** <start> to <end>
**Authorization:** <ROE reference>
**Tester:** <name>

---

## 1. Executive Summary

One page. For the board or the buyer. Risk in business terms, not tool output.

- Overall risk rating: Critical / High / Medium / Low
- What an attacker could achieve today
- The three things to fix first

---

## 2. Scope

- Targets tested (models, endpoints, input paths, connected tools)
- Explicitly out of scope
- Attack classes covered (OWASP LLM Top 10 references)

---

## 3. Findings

Repeat per finding.

### F-01: <title>

| Field | Value |
|-------|-------|
| Severity | Critical / High / Medium / Low |
| OWASP LLM | LLM0x |
| MITRE ATLAS | AML.Txxxx |
| Input path | chat / document / RAG / tool output |

**Description.** What the model did that it should not have.

**Reproduction.**
1. Step
2. Step

**Evidence.** Prompt and response, redacted as needed.

**Impact.** What this lets an attacker do.

**Remediation.** Specific fix. Input validation, output filtering, guardrail, least-privilege on tools, model change.

---

## 4. Framework Roll-Up

| NIST AI RMF function | Findings | Gap summary |
|----------------------|----------|-------------|
| Govern | | |
| Map | | |
| Measure | | |
| Manage | | |

ISO 42001 control gaps (for clients pursuing certification): <list>

---

## 5. Remediation Roadmap

Prioritized. Re-test offer once fixes land.

| Priority | Finding | Owner | Re-test |
|----------|---------|-------|---------|

---

## 6. Appendix

- Tooling and versions (garak, PyRIT, promptfoo, PurpleLlama, ModelScan)
- Full probe logs
- Rules of engagement
