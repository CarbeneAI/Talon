# OSCP-Style Penetration Test Report Template

Professional report structure for client engagements, OSCP exam submissions, and bug bounty writeups.

---

## Report Structure

```
# Penetration Test Report

**Client:** [Client Name]
**Assessment Type:** [Internal / External / Web Application / Full Scope]
**Date:** [Start Date] - [End Date]
**Tester:** [Your Name / Team]
**Report Version:** 1.0

---

## Executive Summary

[2-3 paragraph high-level summary for non-technical stakeholders. Explain what was tested,
what was found, and what the business impact is — without technical jargon.]

Key findings:
- [Critical finding count] Critical vulnerabilities
- [High finding count] High severity vulnerabilities
- [Medium/Low counts] Medium and Low severity vulnerabilities

---

## Scope

### In-Scope Assets

| Asset | IP Address | Description |
|-------|------------|-------------|
| [Name] | [IP] | [Description] |

### Out-of-Scope

- [Items explicitly excluded from testing]

### Testing Methodology

This assessment followed [OWASP / PTES / OSSTMM] methodology, including:

1. Reconnaissance and information gathering
2. Vulnerability identification and analysis
3. Exploitation
4. Post-exploitation and lateral movement
5. Reporting and remediation recommendations

---

## Findings Summary

| ID | Title | Severity | CVSS | Status |
|----|-------|----------|------|--------|
| 1 | [Title] | Critical | 9.8 | Open |
| 2 | [Title] | High | 7.5 | Open |
| 3 | [Title] | Medium | 5.0 | Open |

---

## Detailed Findings

### Finding 1: [Vulnerability Title]

**Severity:** Critical
**CVSS Score:** 9.8
**Affected Asset:** [IP/hostname]
**Service/Port:** [Service name on port number]

#### Description

[Detailed technical description of the vulnerability.]

#### Evidence

[Screenshots, command outputs, proof of exploitation]

#### Steps to Reproduce

1. [Step 1 with specific commands]
2. [Step 2]
3. [Continue until exploitation is demonstrated]

#### Impact

- [Impact point 1]
- [Impact point 2]

#### Remediation

1. [Primary recommendation]
2. [Secondary recommendation]

**References:**
- [CVE link if applicable]
- [Vendor advisory]

---

## Attack Narrative

### Initial Access

[How initial foothold was gained]

### Privilege Escalation

[How privileges were escalated to root/SYSTEM]

### Flags / Proof

local.txt:  [hash]
proof.txt:  [hash]

---

## Appendices

### Appendix A: Full Tool Output

[Full nmap scans, vulnerability scanner output]

### Appendix B: Credentials Discovered

| Username | Password / Hash | Location Found | Valid On |
|----------|----------------|----------------|----------|
| [user] | [credential] | [where found] | [systems] |

### Appendix C: Remediation Priority Matrix

| Priority | Finding | Effort | Risk Reduction |
|----------|---------|--------|----------------|
| 1 | [Title] | Low | High |
| 2 | [Title] | Medium | High |
```

---

## Quick Finding Template

```
### Finding X: [Title]

**Severity:** [Critical / High / Medium / Low / Info]
**CVSS:** [Score]
**Asset:** [IP/hostname]
**Port/Service:** [port/service]

#### Description
[What is the vulnerability and why does it exist]

#### Evidence
[Proof - command output, screenshot reference]

#### Steps to Reproduce
1.
2.
3.

#### Impact
[Business and technical impact]

#### Remediation
[How to fix - be specific]
```

---

## Severity Definitions

| Severity | CVSS Range | Description |
|----------|------------|-------------|
| Critical | 9.0 - 10.0 | Immediate action required. Full system compromise likely. |
| High | 7.0 - 8.9 | Significant vulnerability. Fix within 30 days. |
| Medium | 4.0 - 6.9 | Moderate risk. Schedule remediation within 90 days. |
| Low | 0.1 - 3.9 | Minor issue. Fix in next maintenance window. |
| Info | N/A | Informational finding or best practice suggestion. |

---

## OSCP-Specific Notes

- Include screenshots of every significant step
- Show `id` or `whoami` output after each shell obtained
- Include proof.txt / local.txt contents alongside `hostname` and `ip addr` output
- Document exact methodology including failed attempts
- Keep it professional and thorough
