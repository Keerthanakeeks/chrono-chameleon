#!/bin/bash
echo "[*] Shutting down Chrono-Chameleon..."
sudo pkill -f "orchestrator.py"
sudo pkill -f "smart_proxy.py"
sudo pkill -f "server.js"
sudo iptables -F
echo "[+] All systems offline and firewall reset."
