# Talon — Claude Code Project Instructions

Talon is a penetration testing workflow toolkit that connects Claude Code to a Kali Linux VM via SSH MCP.

## MCP Server

The `kali-ssh` MCP server (configured in `mcp-config.example.json`) provides SSH access to your pentest VM. Copy the example config to `~/.claude/mcp.json` and update with your host/username before use.

All shell commands in this project are intended to run **on the remote Kali VM** via the MCP connection, not locally.

## Methodology

Follow the 5-phase pentest methodology defined in `references/` and `SKILL.md`:

1. **Recon** — `scripts/recon.sh <target-ip>` for automated initial recon
2. **Enumeration** — Use `references/service-enum.md` for per-service commands
3. **Exploitation** — Document and execute with searchsploit / metasploit / manual exploits
4. **Post-Exploitation** — PrivEsc enumeration, credential harvesting, persistence
5. **Reporting** — Use `references/report-template.md` for structured findings

## Obsidian Notes

Use templates in `templates/` for engagement tracking:

- `templates/engagement.md` — One per engagement, tracks all targets and credentials
- `templates/target.md` — One per machine, tracks recon, foothold, and PrivEsc

## Key References

- `references/service-enum.md` — Enumeration commands for 13 service types
- `references/report-template.md` — OSCP-style report structure
- `docs/setup-kali.md` — Kali VM setup guide
- `docs/ssh-access.md` — Remote access methods (SSH tunnel, VPN, ngrok, Cloudflare)
- `docs/usage.md` — Example prompts and workflows

## Security Rules

- Always confirm you have written authorization before testing any target
- Never store credentials, flags, or loot in this repository
- Keep scan output and results in local directories (gitignored)
- Rotate SSH keys regularly

## Common Prompts

Ask Claude:

- "Run recon on [IP] using Kali"
- "Enumerate [service] on [IP]"
- "I have a shell as [user] — check for PrivEsc paths"
- "Generate a report for this engagement"
