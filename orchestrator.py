"""
MTD Orchestrator v2 (60% phase):
- pyotp TOTP port rotation (30s epoch, 8000 + TOTP%50)
- MODE-based container switching: node_mtd_image real/trap
- Instant ban queue (honey-token hits)
- Reverse Reconnaissance: nmap scan against trapped attacker IPs
- Auto-blocker: iptables DROP
"""
import ipaddress, json, os, subprocess, threading, time
from datetime import datetime
import docker
import pyotp

SHARED_SECRET = "JBSWY3DPEHPK3PXP"
EPOCH = 30
GRACE_PERIOD = 2
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SHARED = os.path.join(BASE_DIR, "shared_logs")
LOG_PATH = os.path.join(SHARED, "attack.log")
BAN_QUEUE = os.path.join(SHARED, "ban_queue.log")
BAN_STATE = os.path.join(SHARED, "bans.txt")
RECON_PATH = os.path.join(SHARED, "recon.json")
TOTP = pyotp.TOTP(SHARED_SECRET)
DEMO_ALLOW_LOCAL = os.environ.get("DEMO_ALLOW_LOCAL", "0") == "1"

for p in (SHARED,):
    os.makedirs(p, exist_ok=True)
for p in (LOG_PATH, BAN_QUEUE, BAN_STATE, RECON_PATH):
    open(p, "a").close()

client = docker.from_env()

def port_for_epoch(ts: int) -> int:
    return 8000 + (int(TOTP.at(ts)) % 50)

def current_port() -> int:
    return port_for_epoch(int(time.time()))

def run_container(mode: str, port: int, name: str):
    try:
        client.containers.get(name).remove(force=True)
    except docker.errors.NotFound:
        pass
    if mode == "trap":
        for c in client.containers.list(all=True):
            if c.name.startswith("trap_") and c.name != name:
                try:
                    c.stop(timeout=1)
                    c.remove(force=True)
                    print(f"[orchestrator] cleaned stale trap {c.name}")
                except docker.errors.APIError:
                    pass
    client.containers.run(
        "node_mtd_image",
        name=name,
        environment={"PORT": str(port), "MODE": mode},
        ports={f"{port}/tcp": (port,)},
        network="bridge",
        volumes={SHARED: {"bind": "/shared_logs", "mode": "rw"}},
        detach=True,
    )
    print(f"[orchestrator] deployed {name} ({mode}) on port {port}")

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
            run_container("real", port, f"real_app_{port}")
            if active_port is not None:
                old_port = active_port

                def handoff(op=old_port):
                    time.sleep(GRACE_PERIOD)
                    stop_containers("real_app_")
                    run_container("trap", op, f"trap_{op}") 

                threading.Thread(target=handoff, daemon=True).start()
            active_port = port
            print(f"[orchestrator] epoch shift -> active real_app on port {port}")
        now = time.time()
        time.sleep(max(0.5, EPOCH - (now % EPOCH)))

def reverse_recon(ip: str, port: int):
    print(f"[recon] reverse-scanning attacker {ip} ...")
    try:
        result = subprocess.run(
            ["nmap", "-sT", "-T4", "--top-ports", "100", "-Pn", "--open", ip],
            capture_output=True, text=True, timeout=120)
        open_ports, services = [], []
        for line in result.stdout.splitlines():
            parts = line.split()
            if "/tcp" in line and "open" in line:
                open_ports.append(parts[0])
                services.append(line.strip())
        entry = {
            "ip": ip, "trapped_port": port,
            "nmap_ports": open_ports, "nmap_services": services,
            "os_guess": next((l for l in result.stdout.splitlines()
                              if "Running" in l or "OS details" in l), "unknown"),
            "time": datetime.now().isoformat(),
        }
        with open(RECON_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
        print(f"[recon] DONE {ip}: open ports {open_ports or 'stealth'}")
    except Exception as e:
        print(f"[recon] failed for {ip}: {e}")

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

def block_ip(ip: str, reason: str = "honeypot touch"):
    subprocess.run(["sudo", "iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"],
                   check=False)
    with open(BAN_STATE, "a") as f:
        f.write(json.dumps({"ip": ip, "reason": reason,
                            "time": int(time.time())}) + "\n")
    print(f"[blocker] BANNED {ip} ({reason})")

def instant_ban_queue():
    seen = set()
    with open(BAN_QUEUE) as f:
        for line in f:
            try:
                seen.add(json.loads(line)["ip"])
            except (ValueError, KeyError):
                pass
    while True:
        try:
            with open(BAN_QUEUE) as f:
                for line in f:
                    try:
                        e = json.loads(line)
                    except ValueError:
                        continue
                    ip = e.get("ip")
                    if not ip or ip in seen:
                        continue
                    seen.add(ip)
                    if is_protected(ip):
                        print(f"[blocker] skipping protected IP {ip}")
                        continue
                    block_ip(ip, e.get("reason", "honey-token"))
                    threading.Thread(target=reverse_recon,
                                     args=(ip, e.get("port", 0)),
                                     daemon=True).start()
        except FileNotFoundError:
            pass
        time.sleep(1)

def auto_blocker():
    seen = set()
    with open(LOG_PATH) as f:
        for line in f:
            try:
                seen.add(json.loads(line)["ip"])
            except (ValueError, KeyError):
                pass
    while True:
        try:
            with open(LOG_PATH) as f:
                for line in f:
                    try:
                        e = json.loads(line)
                    except ValueError:
                        continue
                    ip = e.get("ip")
                    if not ip or ip in seen:
                        continue
                    seen.add(ip)
                    if is_protected(ip):
                        print(f"[blocker] skipping protected IP {ip}")
                        continue
                    block_ip(ip, f"touch on port {e.get('port')}")
        except FileNotFoundError:
            pass
        time.sleep(2)

if __name__ == "__main__":
    threading.Thread(target=instant_ban_queue, daemon=True).start()
    threading.Thread(target=auto_blocker, daemon=True).start()
    mtd_cycle()

