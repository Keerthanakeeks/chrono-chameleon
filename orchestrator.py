import ipaddress, json, os, socket, subprocess, sys, threading, time
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
CONTAINERS_PATH = os.path.join(SHARED, "containers.json")
TOTP = pyotp.TOTP(SHARED_SECRET)
DEMO_ALLOW_LOCAL = os.environ.get("DEMO_ALLOW_LOCAL", "0") == "1"

os.makedirs(SHARED, exist_ok=True)
for p in (LOG_PATH, BAN_QUEUE, BAN_STATE, RECON_PATH):
    if not os.path.exists(p):
        open(p, "w", encoding="utf-8").close()

try:
    client = docker.from_env()
    client.ping()
    USE_DOCKER = True
    print("[orchestrator] Connected to Docker daemon.")
except Exception:
    client = None
    USE_DOCKER = False
    print("[orchestrator] Docker not running -> Using native process fallback mode.")

local_procs = {}
local_meta = {}

def sync_containers_json():
    items = []
    for name, meta in list(local_meta.items()):
        proc = local_procs.get(name)
        if proc and proc.poll() is None:
            items.append({"name": name, "status": "Up (Native)", "port": meta["port"]})
    with open(CONTAINERS_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f)

def port_for_epoch(ts: int) -> int:
    return 8000 + (int(TOTP.at(ts)) % 50)

def current_port() -> int:
    return port_for_epoch(int(time.time()))

def run_container(mode: str, port: int, name: str):
    if USE_DOCKER:
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
    else:
        if name in local_procs:
            try:
                local_procs[name].terminate()
            except Exception:
                pass
        if mode == "trap":
            for cname in list(local_procs.keys()):
                if cname.startswith("trap_") and cname != name:
                    try:
                        local_procs[cname].terminate()
                    except Exception:
                        pass
                    local_procs.pop(cname, None)
                    local_meta.pop(cname, None)
        entry = os.path.join(BASE_DIR, "node_app", "server.js")
        env = os.environ.copy()
        env["PORT"] = str(port)
        env["MODE"] = mode
        env["SHARED_LOGS"] = SHARED
        proc = subprocess.Popen(["node", entry], cwd=os.path.dirname(entry), env=env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        local_procs[name] = proc
        local_meta[name] = {"port": port, "mode": mode}
        sync_containers_json()
        print(f"[orchestrator] deployed native {name} ({mode}) on port {port}")

def stop_containers(prefix: str):
    if USE_DOCKER:
        for c in client.containers.list(all=True):
            if c.name.startswith(prefix):
                try:
                    c.stop(timeout=1)
                    c.remove(force=True)
                except docker.errors.APIError:
                    pass
    else:
        for cname in list(local_procs.keys()):
            if cname.startswith(prefix):
                try:
                    local_procs[cname].terminate()
                except Exception:
                    pass
                local_procs.pop(cname, None)
                local_meta.pop(cname, None)
        sync_containers_json()

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
                    stop_containers(f"real_app_{op}")
                    run_container("trap", op, f"trap_{op}")
                threading.Thread(target=handoff, daemon=True).start()
            active_port = port
            print(f"[orchestrator] epoch shift -> active real_app on port {port}")
        now = time.time()
        time.sleep(max(0.5, EPOCH - (now % EPOCH)))

def reverse_recon(ip: str, port: int):
    target_ip = "127.0.0.1" if ip in ("::1", "localhost") else ip
    print(f"[recon] reverse-scanning attacker {ip} (target {target_ip}) ...")
    open_ports, services = [], []
    os_guess = "unknown"
    try:
        result = subprocess.run(
            ["nmap", "-sT", "-T4", "--top-ports", "100", "-Pn", "--open", target_ip],
            capture_output=True, text=True, timeout=60)
        for line in result.stdout.splitlines():
            parts = line.split()
            if "/tcp" in line and "open" in line:
                open_ports.append(parts[0])
                services.append(line.strip())
        os_guess = next((l for l in result.stdout.splitlines()
                         if "Running" in l or "OS details" in l), "unknown")
    except Exception:
        pass
    if not open_ports:
        for p in (22, 80, 135, 445, 3389, 5000, 6060, 8080):
            try:
                with socket.create_connection((target_ip, p), timeout=0.3):
                    open_ports.append(f"{p}/tcp")
                    services.append(f"{p}/tcp open tcp-service")
            except Exception:
                pass
        os_guess = "Windows/Linux Socket Scan"
    entry = {
        "ip": ip, "trapped_port": port,
        "nmap_ports": open_ports, "nmap_services": services,
        "os_guess": os_guess,
        "time": datetime.now().isoformat(),
    }
    with open(RECON_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[recon] DONE {ip}: open ports {open_ports or 'stealth'}")

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
    if os.name != "nt":
        subprocess.run(["sudo", "iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"], check=False)
    with open(BAN_STATE, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ip": ip, "reason": reason, "time": int(time.time())}) + "\n")
    print(f"[blocker] BANNED {ip} ({reason})")

def read_clean_lines(filepath):
    try:
        with open(filepath, "rb") as f:
            raw = f.read().replace(b"\x00", b"").decode("utf-8", errors="ignore")
        return [l.strip() for l in raw.splitlines() if l.strip()]
    except FileNotFoundError:
        return []

def instant_ban_queue():
    seen = set()
    while True:
        for line in read_clean_lines(BAN_QUEUE):
            try:
                e = json.loads(line)
            except ValueError:
                continue
            ip = e.get("ip")
            if not ip or ip in seen:
                continue
            seen.add(ip)
            if is_protected(ip):
                continue
            block_ip(ip, e.get("reason", "honey-token"))
            threading.Thread(target=reverse_recon, args=(ip, e.get("port", 0)), daemon=True).start()
        time.sleep(1)

def auto_blocker():
    seen = set()
    while True:
        for line in read_clean_lines(LOG_PATH):
            try:
                e = json.loads(line)
            except ValueError:
                continue
            ip = e.get("ip")
            if not ip or ip in seen:
                continue
            seen.add(ip)
            if is_protected(ip):
                continue
            block_ip(ip, f"touch on port {e.get('port')}")
        time.sleep(2)

if __name__ == "__main__":
    threading.Thread(target=instant_ban_queue, daemon=True).start()
    threading.Thread(target=auto_blocker, daemon=True).start()
    mtd_cycle()
