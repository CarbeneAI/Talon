# Using Talon with Claude Code

Practical examples and workflows for AI-assisted penetration testing.

## Prerequisites

- Talon MCP configured (see README.md Quick Start)
- SSH connection to Kali VM working
- Written authorization for all target systems

---

## Basic Connection Test

Start by verifying the MCP connection works:

```
"Check if Kali is connected and run uname -a"
```

Expected: Claude runs the command via SSH MCP and returns the kernel version.

---

## Phase 1: Initial Reconnaissance

### Run the automated recon script

```
"Run the recon script on 10.10.10.100 and give me a summary of what's open"
```

Claude will:
1. Execute `~/recon.sh 10.10.10.100` on Kali
2. Parse the nmap output
3. Summarize open ports and services
4. Suggest enumeration priorities

### Custom nmap scan

```
"Run a full TCP scan on 10.10.10.100, then do a detailed scan on all open ports"
```

```
"Do a UDP scan on the top 20 ports of 10.10.10.100"
```

---

## Phase 2: Service Enumeration

### Web application

```
"Port 80 is open. Run a full web enumeration — whatweb, gobuster, and nikto"
```

```
"There's a WordPress site on port 80. Run wpscan and check for vulnerable plugins"
```

```
"Run ffuf to fuzz for virtual hosts on this target"
```

### SMB

```
"Port 445 is open. Enumerate SMB — check for null session access and list all shares"
```

```
"Run enum4linux on 10.10.10.100 and tell me what users and shares are accessible"
```

### LDAP / Active Directory

```
"Port 389 is open. Do an anonymous LDAP bind and dump all objects"
```

```
"Run Kerbrute to enumerate valid users against the domain corp.local"
```

### Database services

```
"MySQL is running on port 3306. Try connecting as root with no password"
```

```
"MSSQL is on 1433. Run the nmap scripts and check if xp_cmdshell is enabled"
```

---

## Phase 3: Exploitation

### Web vulnerabilities

```
"The login form looks vulnerable to SQLi. Run sqlmap on the login endpoint"
```

```
"There's an LFI at ?page=. Try to read /etc/passwd and /etc/shadow"
```

```
"The file upload doesn't validate extensions. Help me craft a PHP webshell bypass"
```

### Service vulnerabilities

```
"searchsploit the ProFTPD 1.3.5 version we found and tell me what exploits are available"
```

```
"Run the EternalBlue check on port 445 and exploit it if vulnerable"
```

### Generating reverse shells

```
"Create a bash reverse shell one-liner back to 10.10.14.5 on port 4444"
```

```
"Generate a PowerShell reverse shell that connects back to my IP"
```

---

## Phase 4: Post-Exploitation

### Linux privilege escalation

```
"I have a shell as www-data. Download and run linpeas, then analyze the output for 
PrivEsc paths"
```

```
"Check sudo -l and list all SUID binaries. Look them up on GTFOBins"
```

```
"Check for writable cron jobs and interesting capabilities"
```

### Windows privilege escalation

```
"I have a shell as IIS AppPool user. Run winPEAS and identify the best PrivEsc path"
```

```
"Check for AlwaysInstallElevated and unquoted service paths"
```

```
"Run Seatbelt to check for stored credentials and interesting registry keys"
```

### Credential harvesting

```
"Search the web root for config files containing database passwords"
```

```
"Run secretsdump against the DC once we have domain admin"
```

---

## Phase 5: Reporting

### Generate a report from the session

```
"Summarize everything we found in this engagement into an OSCP-style report"
```

```
"Format the SQL injection finding using the standard finding template with severity, 
evidence, and remediation"
```

```
"Create an executive summary paragraph for a client report — critical findings were 
RCE via SQLi and default credentials on the admin panel"
```

---

## CTF / OSCP Workflows

### HackTheBox / TryHackMe boxes

```
"I'm working on a HackTheBox machine. IP is 10.10.11.200. Start with recon 
and tell me what to focus on"
```

```
"I got user.txt. The flag is [flag]. Now help me escalate to root"
```

```
"I need to find the proof.txt. I'm running as root — check common locations"
```

### OSCP-style documentation

```
"Screenshot command: show hostname, ip addr, and cat proof.txt in one command"
```

```
"Document the full attack chain from initial recon to root for this machine"
```

---

## Tips for Effective Prompting

1. **Provide context** — Tell Claude what you already know: OS, services, credentials found
2. **Specify the tool** — "Use gobuster" vs "enumerate directories" gives better results
3. **Ask for analysis** — "Run X and tell me what's interesting" beats just running the tool
4. **Iterate** — Follow up findings: "That username we found — try it on RDP and WinRM"
5. **Document as you go** — "Add this finding to the report" keeps notes current

---

## Example Full Session

```
1. "Start recon on 10.10.10.100"
   → Automated 5-phase recon runs

2. "Port 22, 80, and 445 are open. What should we look at first?"
   → Claude recommends starting with web (port 80) and SMB

3. "Run web enumeration on port 80"
   → Gobuster finds /admin, /backup, whatweb identifies Apache 2.4.29

4. "Apache 2.4.29 — check for vulnerabilities"
   → searchsploit finds nothing critical, continue to /backup

5. "Check what's in /backup"
   → Contains old config file with database credentials

6. "Try those credentials on SSH"
   → SSH login succeeds as user 'deploy'

7. "Run linpeas as deploy and find PrivEsc"
   → Finds writable cron job running as root

8. "Exploit the cron job"
   → Write reverse shell, catch shell as root

9. "Get proof.txt and document the attack chain"
   → Report generated with full narrative
```
