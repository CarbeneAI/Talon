# Talon — AI Red-Team Pack

**AI-directed adversarial testing for LLM and AI systems.**

Talon's core pack points Claude Code at a Kali VM to test infrastructure. This pack points the same AI-directed, methodology-first workflow at a different target class: the LLM feature and the application around it.

Same idea. You describe the target in plain English. The AI runs the probes, reads the output, correlates findings, and maintains the attack narrative. Different attack surface.

## What it covers

Mapped to the [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/) and [MITRE ATLAS](https://atlas.mitre.org/). Six attack classes:

1. Prompt injection — direct and indirect
2. Jailbreak and guardrail bypass
3. Sensitive information disclosure
4. Tool and agent abuse (function calling, MCP)
5. Model fingerprinting and recon
6. AI supply chain (serialization, provenance)

## Tooling

All open-source, permissive licenses:

| Tool | Role | License |
|------|------|---------|
| [garak](https://github.com/NVIDIA/garak) | LLM vulnerability scanner (injection, jailbreak, leakage) | Apache-2.0 |
| [PyRIT](https://github.com/Azure/PyRIT) | Risk identification, multi-turn attack orchestration | MIT |
| [promptfoo](https://github.com/promptfoo/promptfoo) | Eval + red-team CLI, injection plugins | MIT |
| [PurpleLlama](https://github.com/meta-llama/PurpleLlama) | Llama Guard, CyberSecEval | permissive |
| [ModelScan](https://github.com/protectai/modelscan) | Unsafe model serialization scan | Apache-2.0 |

## Files

- `methodology.md` — the six-phase engagement workflow
- `report-template.md` — findings report structure, framework-tagged

## Authorization

For authorized testing only. Test only systems you own or are explicitly authorized to test, under written rules of engagement. This pack does not include, wrap, or endorse facial-recognition scrapers, breach-data brokers, or tools of unclear provenance.

MIT licensed, same as the rest of Talon.
