---
tags: [target, pentest, <engagement-name>]
ip: 
hostname: 
os: 
status: in-progress
difficulty: 
---

# {{title}}

> [!info] Target Info
> **IP:** `{{ip}}`
> **OS:** {{os}}
> **Difficulty:** {{difficulty}}

## Recon

### Port Scan

```bash
nmap -p- --min-rate 10000 {{ip}} -oN scans/ports.txt
nmap -sC -sV -p <open_ports> {{ip}} -oN scans/detailed.txt
```

**Open Ports:**

| Port | Service | Version |
|------|---------|---------|
|  |  |  |

### Service Enumeration

#### Port X - ServiceName

```bash
# Commands run
```

**Findings:**
- 

## Foothold

### Vulnerability

**CVE/Type:** 
**Affected Service:** 

### Exploitation

```bash
# Exploitation commands
```

**Initial Access As:** 

### user.txt

```
<flag-hash>
```

## Privilege Escalation

### Enumeration

**Interesting Findings:**
- [ ] sudo -l
- [ ] SUID binaries: find / -perm -4000 2>/dev/null
- [ ] Cron jobs: cat /etc/crontab
- [ ] Writable paths
- [ ] Capabilities: getcap -r / 2>/dev/null
- [ ] NFS exports: cat /etc/exports

### PrivEsc Vector

**Method:** 

```bash
# PrivEsc commands
```

### root.txt / proof.txt

```
<flag-hash>
```

## Credentials

| Username | Password/Hash | Source |
|----------|--------------|--------|
|  |  |  |

## Lessons Learned

- 

## References

- https://gtfobins.github.io/
- https://lolbas-project.github.io/
