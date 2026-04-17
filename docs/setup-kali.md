# Setting Up a Kali Linux Pentesting VM

This guide walks through setting up a Kali Linux VM for use with Talon and Claude Code.

## Option 1: Proxmox VM (Recommended for Homelab)

1. Download Kali Linux ISO from https://www.kali.org/get-kali/
2. Create a new VM in Proxmox:
   - CPU: 4 cores minimum
   - RAM: 4GB minimum (8GB recommended)
   - Storage: 50GB minimum
   - Network: Bridge to your LAN
3. Boot from ISO and install Kali
4. After install, note the VM's IP address

## Option 2: VMware / VirtualBox

1. Download the Kali Linux VM image: https://www.kali.org/get-kali/#kali-virtual-machines
2. Import into VMware or VirtualBox
3. Set network adapter to Bridged (so it gets a LAN IP)
4. Start the VM and note the IP

## Option 3: VPS (Cloud-based)

Run Kali on a cloud provider for remote access:

```bash
# DigitalOcean, Linode, Vultr, etc.
# Use a Kali-based image or install manually on Ubuntu:
curl -fsSL https://raw.githubusercontent.com/t3l3machus/kali-scripts/main/install-kali-tools.sh | bash
```

## Initial Kali Configuration

After install, run these setup steps:

```bash
# Update system
sudo apt update && sudo apt full-upgrade -y

# Install common pentest tools (if using minimal install)
sudo apt install -y nmap gobuster feroxbuster nikto smbclient smbmap enum4linux \
    crackmapexec evil-winrm impacket-scripts python3-impacket \
    whatweb ffuf wfuzz nuclei curl wget git python3 python3-pip

# Install linpeas/winpeas
wget https://github.com/carlospolop/PEASS-ng/releases/latest/download/linpeas.sh
chmod +x linpeas.sh

# Install wordlists
sudo apt install -y wordlists
sudo gunzip /usr/share/wordlists/rockyou.txt.gz

# Set up SSH server
sudo apt install -y openssh-server
sudo systemctl enable ssh
sudo systemctl start ssh

# Check IP
ip addr show | grep "inet "
```

## SSH Key Setup for Talon

Configure key-based SSH so Claude Code can connect without password prompts:

```bash
# On your workstation (where Claude Code runs):
ssh-keygen -t ed25519 -C "claude-code-pentest" -f ~/.ssh/kali_pentest

# Copy public key to Kali VM:
ssh-copy-id -i ~/.ssh/kali_pentest.pub YOUR_USERNAME@YOUR_KALI_IP

# Test connection:
ssh -i ~/.ssh/kali_pentest YOUR_USERNAME@YOUR_KALI_IP "uname -a"
```

Then reference your key in the MCP config if needed, or add to `~/.ssh/config`:

```
Host kali
    HostName YOUR_KALI_IP
    User YOUR_USERNAME
    IdentityFile ~/.ssh/kali_pentest
```

## Recommended Directory Structure on Kali

```
~/
├── recon.sh              # Talon's recon script (copy from Talon repo)
├── engagements/
│   └── [engagement-name]/
│       ├── recon/        # nmap output, whatweb, etc.
│       ├── exploitation/ # exploits, shells
│       ├── screenshots/  # proof screenshots
│       └── loot/         # credentials, files
├── tools/
│   ├── linpeas.sh
│   ├── winPEAS.exe
│   └── [other tools]
└── wordlists/            # Symlink or copy from /usr/share/wordlists/
```

## Copy Talon Recon Script to Kali

```bash
scp /path/to/Talon/scripts/recon.sh YOUR_USERNAME@YOUR_KALI_IP:~/recon.sh
ssh YOUR_USERNAME@YOUR_KALI_IP "chmod +x ~/recon.sh"
```

## Security Hardening (Recommended)

Even for a lab VM, basic hardening is good practice:

```bash
# Disable password auth, use keys only
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart ssh

# Set up UFW (optional for lab use)
sudo apt install -y ufw
sudo ufw allow ssh
sudo ufw enable
```

## Verify Talon Connection

Once SSH is configured, verify Claude Code can connect:

1. Update `~/.claude/mcp.json` with your Kali IP and username
2. Restart Claude Code
3. Ask Claude: "Run `uname -a` on Kali and tell me the kernel version"
4. If it responds with kernel info, Talon is working

## Troubleshooting

**SSH connection refused:**
- Check `sudo systemctl status ssh` on Kali
- Verify IP address with `ip addr`
- Check firewall: `sudo ufw status`

**Permission denied:**
- Verify key is in `~/.ssh/authorized_keys` on Kali
- Check key permissions: `chmod 600 ~/.ssh/kali_pentest`
- Check authorized_keys permissions: `chmod 600 ~/.ssh/authorized_keys` on Kali

**MCP server not connecting:**
- Check `npx --version` on your workstation
- Try running MCP server manually: `npx -y @anthropic-ai/mcp-server-ssh ssh://YOUR_USERNAME@YOUR_KALI_IP`
- Review Claude Code logs for MCP connection errors
