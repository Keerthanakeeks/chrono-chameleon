#!/bin/bash
echo "[*] Initializing Chrono-Chameleon Defense Grid..."

echo "[*] Resetting firewall and clearing old logs..."
sudo iptables -F
> /home/kali/mtd/shared_logs/attack.log
> /home/kali/mtd/shared_logs/bans.txt
> /home/kali/mtd/shared_logs/recon.json
rm -f /home/kali/mtd/shared_logs/ban_queue.log

echo "[*] Launching MTD Orchestrator..."
nohup env DEMO_ALLOW_LOCAL=1 /home/kali/mtd/venv/bin/python3 /home/kali/mtd/orchestrator.py > /dev/null 2>&1 &

echo "[*] Launching Smart Proxy..."
nohup /home/kali/mtd/venv/bin/python3 /home/kali/mtd/smart_proxy.py > /dev/null 2>&1 &

echo "[*] Launching SOC Control Center..."
cd /home/kali/mtd/soc && nohup sudo node server.js > /dev/null 2>&1 &

echo "[+] Chrono-Chameleon is LIVE! Systems running in background."
