#!/bin/bash
#
# recon.sh - Automated initial reconnaissance for penetration testing
# Usage: ./recon.sh <target-ip> [output-dir]
#
# Part of Talon - Penetration Testing MCP for Claude Code
# https://github.com/CarbeneAI/Talon
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check arguments
if [ -z "$1" ]; then
    echo -e "${RED}Usage: $0 <target-ip> [output-dir]${NC}"
    echo "Example: $0 10.10.10.100"
    echo "Example: $0 10.10.10.100 ./target-name"
    exit 1
fi

TARGET=$1
OUTDIR=${2:-"./$TARGET"}

# Create output directory
mkdir -p "$OUTDIR"
cd "$OUTDIR"

echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       AUTOMATED RECON - $TARGET       ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}[*] Output directory: $(pwd)${NC}"

# Function to check if command exists
cmd_exists() {
    command -v "$1" &> /dev/null
}

# Phase 1: Quick port scan
echo -e "\n${GREEN}[+] Phase 1: Quick TCP port discovery${NC}"
if cmd_exists nmap; then
    echo -e "${YELLOW}[*] Running: nmap -p- --min-rate 10000 -oN ports.txt${NC}"
    nmap -p- --min-rate 10000 "$TARGET" -oN ports.txt 2>/dev/null

    # Extract open ports
    PORTS=$(grep "^[0-9]" ports.txt 2>/dev/null | cut -d'/' -f1 | tr '\n' ',' | sed 's/,$//')

    if [ -n "$PORTS" ]; then
        echo -e "${GREEN}[+] Open ports found: $PORTS${NC}"

        # Phase 2: Detailed scan on open ports
        echo -e "\n${GREEN}[+] Phase 2: Detailed service enumeration${NC}"
        echo -e "${YELLOW}[*] Running: nmap -sC -sV -p$PORTS -oN detailed.txt${NC}"
        nmap -sC -sV -p"$PORTS" "$TARGET" -oN detailed.txt 2>/dev/null
    else
        echo -e "${RED}[-] No open ports found${NC}"
    fi
else
    echo -e "${RED}[-] nmap not found, skipping port scan${NC}"
fi

# Phase 3: UDP quick scan
echo -e "\n${GREEN}[+] Phase 3: UDP top ports scan${NC}"
if cmd_exists nmap; then
    echo -e "${YELLOW}[*] Running: nmap -sU --top-ports 20 -oN udp.txt${NC}"
    sudo nmap -sU --top-ports 20 "$TARGET" -oN udp.txt 2>/dev/null || \
        echo -e "${YELLOW}[!] UDP scan requires root - skipping${NC}"
fi

# Phase 4: Web enumeration (if port 80 or 443 is open)
if echo "$PORTS" | grep -qE "(^|,)(80|443|8080|8443)(,|$)"; then
    echo -e "\n${GREEN}[+] Phase 4: Web enumeration${NC}"

    # Determine protocol
    if echo "$PORTS" | grep -qE "(^|,)(443|8443)(,|$)"; then
        URL="https://$TARGET"
    else
        URL="http://$TARGET"
    fi

    # Whatweb
    if cmd_exists whatweb; then
        echo -e "${YELLOW}[*] Running: whatweb $URL${NC}"
        whatweb "$URL" -a 3 > whatweb.txt 2>/dev/null || true
    fi

    # Gobuster
    if cmd_exists gobuster; then
        WORDLIST="/usr/share/wordlists/dirb/common.txt"
        if [ -f "$WORDLIST" ]; then
            echo -e "${YELLOW}[*] Running: gobuster dir -u $URL${NC}"
            gobuster dir -u "$URL" -w "$WORDLIST" -x php,txt,html -o gobuster.txt 2>/dev/null || true
        else
            echo -e "${YELLOW}[!] Wordlist not found at $WORDLIST${NC}"
        fi
    elif cmd_exists feroxbuster; then
        echo -e "${YELLOW}[*] Running: feroxbuster -u $URL${NC}"
        feroxbuster -u "$URL" -o feroxbuster.txt 2>/dev/null || true
    fi

    # Nikto
    if cmd_exists nikto; then
        echo -e "${YELLOW}[*] Running: nikto -h $URL (this may take a while)${NC}"
        nikto -h "$URL" -o nikto.txt 2>/dev/null &
        NIKTO_PID=$!
        echo -e "${YELLOW}[*] Nikto running in background (PID: $NIKTO_PID)${NC}"
    fi
fi

# Phase 5: SMB enumeration (if port 445 is open)
if echo "$PORTS" | grep -qE "(^|,)(139|445)(,|$)"; then
    echo -e "\n${GREEN}[+] Phase 5: SMB enumeration${NC}"

    if cmd_exists smbclient; then
        echo -e "${YELLOW}[*] Running: smbclient -L //$TARGET -N${NC}"
        smbclient -L "//$TARGET" -N > smb-shares.txt 2>/dev/null || true
    fi

    if cmd_exists smbmap; then
        echo -e "${YELLOW}[*] Running: smbmap -H $TARGET${NC}"
        smbmap -H "$TARGET" > smbmap.txt 2>/dev/null || true
    fi

    if cmd_exists enum4linux; then
        echo -e "${YELLOW}[*] Running: enum4linux -a $TARGET${NC}"
        enum4linux -a "$TARGET" > enum4linux.txt 2>/dev/null &
        ENUM_PID=$!
        echo -e "${YELLOW}[*] enum4linux running in background (PID: $ENUM_PID)${NC}"
    fi
fi

# Summary
echo -e "\n${BLUE}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              RECON COMPLETE                ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}[+] Results saved to: $(pwd)${NC}"
echo -e "${GREEN}[+] Files created:${NC}"
ls -la *.txt 2>/dev/null || echo "  (no output files yet)"
echo ""
echo -e "${YELLOW}[*] Next steps:${NC}"
echo "  1. Review detailed.txt for service versions"
echo "  2. Check for known vulnerabilities: searchsploit <service> <version>"
echo "  3. Deep dive into interesting services using references/service-enum.md"
