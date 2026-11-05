"""
MTD Orchestrator & Auto-Blocker:
- TOTP port derivation (pyotp, 30s epoch, 8000 + TOTP%50)
- Rolls real_app each epoch -> grace period -> honeypot on vacated port
- Cleans stale honeypots (only ONE trap live at a time)
- Auto-blocker thread tails attack.log and bans attacker IPs via iptables
"""
import ipaddress
import os
import subprocess
import threading
import time

import docker
import pyotp

SHARED_SECRET = "JBSWY3DPEHPK3PXP"
EPOCH = 30
GRACE_PERIOD = 2
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE_DIR, "shared_logs", "attack.log")
BAN_STATE = os.path.join(BASE_DIR, "shared_logs", "bans.txt")
TOTP = pyotp.TOTP(SHARED_SECRET)

# DEMO mode: allow localhost bans so the demo machine can show iptables rules.
# Set DEMO_ALLOW_LOCAL=1 only for demos. Normal runs keep localhost protected.
DEMO_ALLOW_LOCAL = os.environ.get("DEMO_ALLOW_LOCAL", "0") == "1"


def port_for_epoch(ts: int) -> int:
    return 8000 + (int(TOTP.at(ts)) % 50)


def current_port() -> int:
    return port_for_epoch(int(time.time()))


client = docker.from_env()


def clean_stale_honeypots(keep_name: str):
    """Only ONE honeypot live at a time — stop all others."""
    for c in client.containers.list(all=True):
        if c.name.startswith("honeypot_") and c.name != keep_name:
            try:
                c.stop(timeout=1)
                c.remove(force=True)
                print(f"[orchestrator] cleaned stale honeypot {c.name}")
            except docker.errors.APIError:
                pass


def run_container(image: str, port: int, name: str):
    try:
        client.containers.get(name).remove(force=True)
    except docker.errors.NotFound:
        pass
    if image == "honeypot_image":
        clean_stale_honeypots(name)
    client.containers.run(
        image,
        name=name,
        environment={"PORT": str(port)},
        ports={f"{port}/tcp": (port,)},
        network="bridge",
        volumes={os.path.join(BASE_DIR, "shared_logs"): {
            "bind": "/shared_logs", "mode": "rw"}},
        detach=True,
    )
    print(f"[orchestrator] deployed {name} ({image}) on port {port}")


def stop_containers(prefix: str):
    for c in client.containers.list(all=True):
        if c.name.startswith(prefix):
            try:
                c.stop(timeout=1)
                c.remove(force=True)
                print(f"[orchestrator] removed {c.name}")
            except docker.errors.APIError:
                pass


def mtd_cycle():
    active_port = None
    while True:
        port = current_port()
        if port != active_port:
            # 1. Spin up real_app on the new active port
            run_container("real_app_image", port, f"real_app_{port}")
            if active_port is not None:
                old_port = active_port

                def handoff(op=old_port):
                    # 2. Grace period
                    time.sleep(GRACE_PERIOD)
                    # 3. Stop old real_app containers
                    stop_containers("real_app_")
                    # 4. Deploy honeypot on the vacated port
                    run_container("honeypot_image", op, f"honeypot_{op}")

                threading.Thread(target=handoff, daemon=True).start()
            active_port = port
            print(f"[orchestrator] epoch shift -> active real_app on port {port}")
        now = time.time()
        time.sleep(max(0.5, EPOCH - (now % EPOCH)))


# ---------------- Auto-Blocker (Module 5) ----------------
PROTECTED_NETS = [ipaddress.ip_network(n) for n in (
    "127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
)]


def is_protected(ip: str) -> bool:
    if DEMO_ALLOW_LOCAL:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return (addr.is_loopback or addr.is_private or addr.is_unspecified
            or addr.is_multicast or any(addr in n for n in PROTECTED_NETS))


def block_ip(ip: str):
    subprocess.run(["sudo", "iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"],
                   check=False)
    with open(BAN_STATE, "a") as f:
        f.write(f"{ip} {int(time.time())}\n")
    print(f"[blocker] BANNED {ip}")


def auto_blocker():
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    open(LOG_PATH, "a").close()
    seen = set()
    with open(LOG_PATH) as f:
        for line in f:
            parts = line.split()
            if parts:
                seen.add(parts[0])
    while True:
        try:
            with open(LOG_PATH) as f:
                for line in f:
                    parts = line.split()
                    if not parts:
                        continue
                    ip = parts[0]
                    if ip in seen:
                        continue
                    seen.add(ip)
                    if is_protected(ip):
                        print(f"[blocker] skipping protected IP {ip}")
                        continue
                    print(f"[blocker] attacker {ip} trapped")
                    block_ip(ip)
        except FileNotFoundError:
            pass
        time.sleep(2)


if __name__ == "__main__":
    threading.Thread(target=auto_blocker, daemon=True).start()
    mtd_cycle()
