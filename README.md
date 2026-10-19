<p align="center">
  <img src="images/banner.svg" alt="Talon Banner" width="100%">
</p>

# Talon

**Penetration Testing MCP for Claude Code**

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Platform: Claude Code](https://img.shields.io/badge/Platform-Claude_Code-purple.svg)

Talon provides a workflow for using Claude Code with a separately configured SSH MCP provider and a Kali Linux (or other pentesting) VM. It includes automated recon, structured enumeration, and reporting templates.

---

## About CarbeneAI

Talon is one of four open-source AI security proofs of concept published by CarbeneAI, alongside [Harbinger](https://github.com/CarbeneAI/Harbinger) (AI threat intel), [Specter](https://github.com/CarbeneAI/Specter) (AI-assisted SIEM), and [Forge](https://github.com/CarbeneAI/Forge) (AI operations platform). They are not the product. They exist so prospects can see CarbeneAI's founder, Clint P. Garrison, understands the end-to-end strategy of AI in security operations.

CarbeneAI is a Fractional CTO + CISO + AI Strategy advisory practice for CEOs and Boards in risk-driven environments. Clint owns the strategy and risk seat at the client table; CarbeneAI's team and partner network deliver execution.

Use this repo. Fork it. Improve it. For CarbeneAI advisory engagement: [carbene.ai](https://carbene.ai)

---

## What It Does

Talon provides a penetration testing methodology for use with an SSH MCP server you supply and review:

- **AI-directed recon** — Ask Claude to run nmap, gobuster, or nikto and get structured analysis
- **Automated 5-phase reconnaissance** — Port discovery, service enumeration, web scanning, SMB, UDP
- **13-service enumeration guide** — Comprehensive commands for every common service
- **OSCP-style report template** — Professional reporting structure for client and certification use
- **Obsidian vault integration** — Engagement and target note templates for organized documentation

The key insight: Claude can execute commands on your Kali VM, interpret the output, suggest next steps, and maintain a complete attack narrative — without leaving your editor.

---

## Features

| Feature | Description |
|---------|-------------|
| SSH MCP workflow | Use your separately configured SSH MCP provider to access your pentest VM |
| Automated recon | 5-phase bash script covering all initial recon steps |
| Service enumeration | 13 services: FTP, SSH, SMB, HTTP, Kerberos, LDAP, MSSQL, MySQL, RDP, WinRM, Redis, PostgreSQL, SMTP |
| Report generation | OSCP-style template with findings, evidence, and remediation structure |
| Obsidian templates | Engagement tracker and per-target notes with attack path mermaid diagrams |
| Dark workflow | Built for terminal-first, low-noise operation |

---

## Requirements

- [Claude Code](https://claude.ai/code) installed and running
- SSH access to a Kali Linux (or other pentesting) VM
- A reviewed SSH MCP server and the runtime required by that provider
- Target systems you have explicit authorization to test

---

## Quick Start

### 1. Select an SSH MCP Server

Talon does not bundle an SSH MCP implementation or provide a tested provider.
Choose and review a provider, then follow its installation and SSH authentication
instructions. The server command, arguments, runtime, and host/key configuration
are provider-specific. Selecting and validating a default provider remains open.

### 2. Register Your SSH MCP Server

Run registration commands on your workstation, from the Talon repository root.
For a local stdio provider, the Claude Code CLI syntax is:

```text
claude mcp add --transport stdio --scope local kali-ssh -- <command> [args...]
```

Replace `<command> [args...]` with your reviewed provider's actual launch command
and arguments. This is syntax guidance, not a working SSH server command.
Local scope stores the registration in `~/.claude.json` for this project.

For a shared project configuration, Claude Code uses `.mcp.json` at the project
root. [mcp-config.example.json](mcp-config.example.json) shows the structure only;
replace its command and arguments using the provider's documentation before use.
The root `.mcp.json` is ignored for local use. Do not overwrite an existing
configuration or commit credentials or private keys.
See the [official Claude Code MCP documentation](https://code.claude.com/docs/en/mcp)
for registration, configuration scopes, and project server approval.

### 3. Set Up SSH Key Auth

Set up SSH authentication on your workstation and configure your chosen provider
to use it. A successful SSH check alone does not verify the MCP integration:

```bash
# Generate a key if you don't have one
ssh-keygen -t ed25519 -C "claude-code-pentest"

# Copy to your Kali VM
ssh-copy-id YOUR_USERNAME@YOUR_KALI_IP

# Test the connection
ssh YOUR_USERNAME@YOUR_KALI_IP "uname -a"
```

### 4. Copy Recon Script to Your VM

```bash
scp scripts/recon.sh YOUR_USERNAME@YOUR_KALI_IP:~/recon.sh
ssh YOUR_USERNAME@YOUR_KALI_IP "chmod +x ~/recon.sh"
```

### 5. Verify the MCP Connection

Run `claude mcp get kali-ssh`, then open Claude Code in this project and check
`/mcp`. Approve a reviewed project-scoped server if prompted. Ask for `uname -a`
on your Kali VM to verify command execution before testing an authorized target.
This repository does not establish that any particular SSH MCP provider works.

Once your connection works, start asking:

- "Run a full recon on 10.10.10.100 using Kali"
- "Enumerate SMB shares on the target"
- "Check for web vulnerabilities on http://10.10.10.100"
- "Run linpeas and analyze the output"
- "Generate a pentest report for this engagement"

See `docs/usage.md` for complete workflow examples.

---

## Repository Structure

```
Talon/
├── mcp-config.example.json      # MCP structure template; requires a real provider
├── .env.example                 # Optional reference values; provider support required
├── CLAUDE.md                    # Claude Code project instructions
├── scripts/
│   └── recon.sh                 # Automated 5-phase reconnaissance
├── references/
│   ├── service-enum.md          # Per-service enumeration commands (13 services)
│   └── report-template.md       # OSCP-style report template
├── templates/
│   ├── engagement.md            # Obsidian engagement tracker
│   └── target.md                # Obsidian per-target notes
└── docs/
    ├── setup-kali.md            # Kali VM setup guide
    ├── ssh-access.md            # SSH tunnel and VPN access methods
    └── usage.md                 # Usage examples and workflows
```

---

## Methodology

Talon follows a structured 5-phase approach:

```
1. RECON  →  2. ENUM  →  3. EXPLOIT  →  4. POST-EXPLOIT  →  5. REPORT
     |             |            |               |                  |
  Passive      Services     Initial          PrivEsc           Document
  + Active     + Vulns      Access           + Loot            Findings
```

The `scripts/recon.sh` script automates Phase 1 and feeds directly into Phase 2 using the `references/service-enum.md` guide.

---

## Example Prompts for Claude

Once the MCP server is connected, try these prompts:

```
# Initial recon
"Run the recon script on 10.10.10.50 and tell me what's interesting"

# Service deep dive
"Port 445 is open. Enumerate SMB using null session and check for vulnerabilities"

# Web testing  
"The target has a web server on port 80. Run a full web enumeration and check for common vulns"

# Post-exploitation
"I have a shell as www-data. Run linpeas and identify privilege escalation paths"

# Reporting
"Summarize all findings from this session into a professional report"
```

---

## Security and Ethics

**This tool is for authorized security testing only.**

- Always obtain written authorization before testing any system
- Never use against systems you do not own or have explicit permission to test
- Comply with your local laws and the terms of any bug bounty programs
- Store engagement data securely and dispose of it properly after completion

---

## Obsidian Integration

Talon includes Obsidian-compatible templates for maintaining organized pentest notes:

1. Copy `templates/engagement.md` to your Obsidian vault as a new note
2. Copy `templates/target.md` for each machine you test
3. Link targets from the engagement note for a connected knowledge graph

The templates use Obsidian callouts, mermaid diagrams, and checkbox lists for efficient note-taking during active engagements.

---

## Related Projects

- [PAI (Personal AI Infrastructure)](https://github.com/CarbeneAI/PAI) — The open-source AI infrastructure system Talon was extracted from

---

## Offline runner checks

The [AI runner instructions](references/ai-red-team/runner/README.md#tests)
describe 16 offline checks for report handling, mocked command status, supported
configuration validation, and evidence ignore rules. Run them on your workstation; they do
not validate scanners, a live target, or an SSH MCP provider.

## Contributing

See the [proposed roadmap](ROADMAP.md) for reliability and setup improvements
for maintainer discussion. It is not an adopted commitment or timeline.

Pull requests welcome. Focus areas:

- Additional service enumeration guides
- Report template variants (PTES, bug bounty, etc.)
- Obsidian workflow improvements
- Additional automation scripts

---

## License

MIT License. Copyright 2026 CarbeneAI.

See [LICENSE](./LICENSE) for full text.

---

*Built by [CarbeneAI](https://carbene.ai) — Security Built In, Not Bolted On.*
