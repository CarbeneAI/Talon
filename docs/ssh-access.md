# SSH Access Methods for Remote Pentesting VMs

Options for connecting Claude Code to a pentesting VM that is not on your local network.

## Option 1: Direct SSH (Same Network)

The simplest setup — both machines on the same LAN:

```bash
# MCP config
ssh://YOUR_USERNAME@YOUR_KALI_IP
```

No tunneling required. Just ensure SSH is enabled on the VM and key auth is configured.

---

## Option 2: ngrok (Quick Remote Access)

Best for: Quick testing, demo environments, temporary remote access.

### Setup ngrok

```bash
# Install ngrok
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok

# Or via snap
sudo snap install ngrok
```

### Configure and run

```bash
# Sign up at https://ngrok.com (free tier works)
# Get auth token from dashboard
ngrok config add-authtoken YOUR_NGROK_TOKEN

# Expose SSH
ngrok tcp 22
```

Output:
```
Forwarding  tcp://0.tcp.ngrok.io:12345 -> localhost:22
```

Then update your MCP config:
```json
"ssh://YOUR_USERNAME@0.tcp.ngrok.io:12345"
```

### Optional: Add basic auth

```bash
ngrok tcp 22 --basic-auth="username:password"
```

---

## Option 3: SSH Reverse Tunnel

Best for: When your VM is behind NAT and you have a cloud server with a public IP.

### From your Kali VM, connect to your jump server:

```bash
# Forward port 2222 on the jump server back to Kali's SSH
ssh -R 2222:localhost:22 YOUR_USER@YOUR_JUMP_SERVER.com

# Keep it persistent with autossh
sudo apt install -y autossh
autossh -M 0 -f -N -R 2222:localhost:22 YOUR_USER@YOUR_JUMP_SERVER.com
```

### MCP config uses the jump server:

```json
"ssh://YOUR_USERNAME@YOUR_JUMP_SERVER.com:2222"
```

### systemd service for persistence

```ini
[Unit]
Description=SSH Reverse Tunnel to Jump Server
After=network.target

[Service]
User=YOUR_USERNAME
ExecStart=/usr/bin/autossh -M 0 -N -R 2222:localhost:22 YOUR_USER@YOUR_JUMP_SERVER.com
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

---

## Option 4: Tailscale VPN (Easiest Secure Option)

Best for: Permanent remote access with minimal configuration, secure by default.

```bash
# Install on both machines
curl -fsSL https://tailscale.com/install.sh | sh

# Authenticate
sudo tailscale up

# Get Tailscale IP
tailscale ip -4
# Returns something like: 100.x.x.x
```

Update MCP config with Tailscale IP:
```json
"ssh://YOUR_USERNAME@100.x.x.x"
```

Works across networks, NAT-traversal built in, end-to-end encrypted.

---

## Option 5: Cloudflare Tunnel (Production-Grade)

Best for: Permanent access with your own domain, no public IP required.

```bash
# Install cloudflared on Kali VM
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Authenticate with Cloudflare
cloudflared tunnel login

# Create a tunnel
cloudflared tunnel create kali-pentest

# Configure tunnel
cat > ~/.cloudflared/config.yml << CFEOF
tunnel: <TUNNEL_ID>
credentials-file: /home/YOUR_USERNAME/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: kali.yourdomain.com
    service: ssh://localhost:22
  - service: http_status:404
CFEOF

# Route DNS
cloudflared tunnel route dns kali-pentest kali.yourdomain.com

# Run the tunnel
cloudflared tunnel run kali-pentest
```

MCP config:
```json
"ssh://YOUR_USERNAME@kali.yourdomain.com"
```

---

## Option 6: WireGuard VPN

Best for: Maximum performance, self-hosted, whole-network access.

### On the WireGuard server (or router):

```bash
# Install WireGuard
sudo apt install -y wireguard

# Generate server keys
wg genkey | tee server_private.key | wg pubkey > server_public.key

# Server config
cat > /etc/wireguard/wg0.conf << WGEOF
[Interface]
Address = 10.8.0.1/24
ListenPort = 51820
PrivateKey = $(cat server_private.key)

[Peer]
# Kali VM
PublicKey = KALI_PUBLIC_KEY
AllowedIPs = 10.8.0.2/32
WGEOF

sudo systemctl enable wg-quick@wg0
sudo systemctl start wg-quick@wg0
```

### On Kali VM:

```bash
sudo apt install -y wireguard

wg genkey | tee client_private.key | wg pubkey > client_public.key

cat > /etc/wireguard/wg0.conf << WGEOF
[Interface]
Address = 10.8.0.2/24
PrivateKey = $(cat client_private.key)

[Peer]
PublicKey = SERVER_PUBLIC_KEY
Endpoint = SERVER_IP:51820
AllowedIPs = 10.8.0.0/24
PersistentKeepalive = 25
WGEOF

sudo systemctl enable wg-quick@wg0
sudo systemctl start wg-quick@wg0
```

MCP config uses WireGuard IP:
```json
"ssh://YOUR_USERNAME@10.8.0.2"
```

---

## Recommendation Matrix

| Scenario | Method | Difficulty |
|----------|--------|------------|
| Same local network | Direct SSH | Easy |
| Quick remote test | ngrok | Easy |
| Cloud VM with public IP | Direct SSH | Easy |
| VM behind NAT, have jump server | Reverse tunnel | Medium |
| Need permanent remote access | Tailscale | Easy |
| Own domain, no public IP | Cloudflare Tunnel | Medium |
| Maximum performance, self-hosted | WireGuard | Hard |

**For most homelab setups: Tailscale is the easiest permanent solution.**

---

## Security Best Practices

1. **Key-only SSH auth** — Disable password authentication on your pentesting VM
2. **Dedicated SSH key** — Use a separate key for Claude Code MCP, not your main key
3. **Firewall rules** — Restrict SSH access to known IPs where possible
4. **VPN over direct exposure** — Prefer VPN (Tailscale, WireGuard) over exposing SSH directly
5. **Rotate keys** — Rotate SSH keys periodically, especially after engagements
