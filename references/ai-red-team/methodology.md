# AI Red-Team Methodology

Six phases. Run them in order. Each phase feeds the next.

---

## Phase 0 — Scoping & Authorization

Before any probe runs.

- [ ] Written rules of engagement signed
- [ ] Target inventory: which models, which endpoints, which input paths, which connected tools
- [ ] Data-handling agreement: no client data used for training, retention window defined
- [ ] Out-of-scope list: production systems, real user data, connected third parties
- [ ] Success criteria and reporting cadence agreed

Output: scoped engagement, authorized targets, a map of every input path the model can read from.

---

## Phase 1 — Recon & Fingerprinting

Identify the model and its capabilities before attacking. What you are testing shapes every attack that follows.

- Model identification with minimal queries (LLMmap-style behavioral fingerprinting)
- Capability discovery: system prompt hints, refusal patterns, context window, tool access
- Enumerate input paths: chat, uploaded documents, retrieved records (RAG), tool outputs

Tooling: `garak` probe suite, manual capability probes.

---

## Phase 2 — Prompt Injection (Direct & Indirect)

The single highest-impact class. Test every path the model reads from, not just the chat box.

- **Direct:** instructions in user input that override the system prompt
- **Indirect:** instructions hidden in content the model ingests — a document, a web page, a database record pulled via RAG, the output of a connected tool
- Payload delivery across all Phase 1 input paths

Tooling: `promptfoo` injection plugins, `PyRIT` orchestrators. Reference: OWASP LLM01.

---

## Phase 3 — Jailbreak & Guardrail Bypass

Get the model to do what policy forbids.

- Known jailbreak families (role-play, hypothetical framing, encoding)
- Adversarial-suffix techniques where the model is white-box or gradient-accessible
- Guardrail evasion against any input/output classifier in place

Tooling: `garak` jailbreak probes, `PyRIT`, `PurpleLlama` Llama Guard for defense baseline.

---

## Phase 4 — Sensitive Information Disclosure

What the model says that it should never say.

- System-prompt extraction
- Training-data and memorization leakage
- PII exposure and, in multi-tenant apps, cross-tenant leakage
- Secret and credential leakage from context

Tooling: `garak` leakage probes, `PyRIT` multi-turn extraction. Reference: OWASP LLM02 / LLM06.

---

## Phase 5 — Tool & Agent Abuse

Where an AI feature stops being a chatbot and becomes a path into the client's systems. Highest business impact when the model has tools.

- Excessive agency: does the model take actions beyond what the task needs
- Unsafe function calling: parameter injection, unintended tool chains
- MCP tool abuse: prompt injection in tool descriptions, tool output as an injection vector
- Confused-deputy: using the model's authority to reach something the user cannot

Tooling: manual, `PyRIT` orchestration against the live agent. Reference: OWASP LLM07 (excessive agency), MITRE ATLAS.

---

## Phase 6 — AI Supply Chain

The model and its dependencies as an attack surface.

- Unsafe serialization: pickle-based model files that execute code on load
- Model provenance: is the deployed model what the client thinks it is
- Poisoned or typosquatted ML dependencies

Tooling: `ModelScan`, `Fickling`, `picklescan`, `GuardDog`. Reference: OWASP LLM05.

---

## Reporting

Every finding gets: severity, reproduction steps, evidence, OWASP LLM + MITRE ATLAS tags, and remediation. Roll findings up to NIST AI RMF (Govern/Map/Measure/Manage) and flag ISO 42001 control gaps. Use `report-template.md`.
