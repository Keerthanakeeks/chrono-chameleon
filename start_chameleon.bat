@echo off
echo [*] Initializing Chrono-Chameleon Defense Grid on Windows...
if not exist shared_logs mkdir shared_logs
type nul > shared_logs\attack.log
type nul > shared_logs\bans.txt
type nul > shared_logs\recon.json
if exist shared_logs\ban_queue.log del /f /q shared_logs\ban_queue.log

echo [*] Launching MTD Orchestrator...
start "MTD Orchestrator" cmd /k "set DEMO_ALLOW_LOCAL=1 && venv\Scripts\python.exe orchestrator.py"

echo [*] Launching Smart Proxy (Port 5000)...
start "Smart Proxy" cmd /k "venv\Scripts\python.exe smart_proxy.py"

echo [*] Launching SOC Control Center (Port 6060)...
start "SOC Control Center" cmd /k "cd soc && node server.js"

echo [+] Chrono-Chameleon is LIVE!
