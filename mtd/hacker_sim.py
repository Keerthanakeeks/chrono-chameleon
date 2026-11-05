"""
Hacker Simulation — behaves like a real automated attacker:
Phase 1: Port sweep (nmap-style scan across the MTD range)
Phase 2: Service fingerprinting on discovered open ports
Phase 3: Path fuzzing / exploitation attempts against the "found" service
"""
import random
import socket
from datetime import datetime

import requests

TARGET_HOST = "127.0.0.1"   # change to your LAN IP for a full demo ban
PORT_START, PORT_END = 8000, 8050

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "sqlmap/1.8#stable (https://sqlmap.org)",
    "Nikto/2.5.0",
    "Mozilla/5.0 (compatible; Nmap Scripting Engine; https://nmap.org/book/nse.html)",
    "curl/8.5.0",
    "python-requests/2.31.0",
]

ATTACK_PATHS = [
    "/", "/admin", "/admin/login", "/wp-admin", "/.env", "/phpmyadmin",
    "/login", "/api/v1/users", "/../../etc/passwd", "/config.php.bak",
    "/shell.jsp", "/actuator/env", "/.git/config", "/backup.zip",
]


def banner(msg: str):
    print(f"\033[91m[{datetime.now().strftime('%H:%M:%S')}] {msg}\033[0m")


def recon_tcp_sweep():
    """Phase 1 — SYN-style connect sweep across the whole MTD port range."""
    banner("[RECON] Initiating TCP connect sweep across port range 8000-8050 ...")
    open_ports = []
    for port in range(PORT_START, PORT_END + 1):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.05)
        try:
            if s.connect_ex((TARGET_HOST, port)) == 0:
                open_ports.append(port)
        finally:
            s.close()
    banner(f"[RECON] Sweep complete. Open ports discovered: {open_ports or 'NONE'}")
    return open_ports


def fingerprint(port: int):
    """Phase 2 — grab banner/headers to fingerprint the service."""
    banner(f"[FINGERPRINT] Probing service on port {port} ...")
    try:
        r = requests.get(f"http://{TARGET_HOST}:{port}/", timeout=3,
                         headers={"User-Agent": random.choice(USER_AGENTS)})
        server = r.headers.get("Server", "unknown")
        banner(f"[FINGERPRINT] HTTP {r.status_code} | Server: {server} | len={len(r.content)}")
        if "IIS" in server or "Microsoft" in server:
            banner("[FINGERPRINT] Target identified: Windows IIS server — switching to ASP.NET exploits")
        return server
    except requests.RequestException as e:
        banner(f"[FINGERPRINT] Connection reset — target moved? ({e.__class__.__name__})")
        return None


def fuzz_and_exploit(port: int):
    """Phase 3 — hammer the discovered port with common vuln paths."""
    banner(f"[EXPLOIT] Launching path fuzzing attack against port {port} ...")
    hit = False
    for path in ATTACK_PATHS:
        try:
            r = requests.get(f"http://{TARGET_HOST}:{port}{path}", timeout=3,
                             headers={"User-Agent": random.choice(USER_AGENTS)})
            banner(f"[EXPLOIT] {path:<22} -> HTTP {r.status_code}")
            if r.status_code == 403:
                hit = True
        except requests.RequestException:
            banner(f"[EXPLOIT] {path:<22} -> connection dropped (tarpit?)")
    return hit


def main():
    banner("=" * 60)
    banner("      AUTOMATED ATTACK SIMULATION — BLACK BOX MODE")
    banner("=" * 60)

    # NOTE: hacker does NOT know the TOTP secret — he only scans blindly.
    open_ports = recon_tcp_sweep()
    if not open_ports:
        banner("[RESULT] No open ports found. MTD moved the target. Attack aborted.")
        return

    banner(f"[DECISION] {len(open_ports)} candidate(s): {open_ports}")

    for target_port in open_ports:
        server = fingerprint(target_port)
        if server and "IIS" in server:
            banner(f"[DECISION] Port {target_port} looks like IIS — suspicious legacy box. Fuzzing!")
            fuzz_and_exploit(target_port)
            banner("[TRAP TRIGGERED] Honeypot logged our IP. Retaliation imminent...")
        else:
            banner(f"[DECISION] Port {target_port} unknown service — light probe only.")
            fuzz_and_exploit(target_port)


if __name__ == "__main__":
    main()
