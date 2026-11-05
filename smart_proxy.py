import threading, time
from collections import defaultdict, deque
import pyotp, requests
from flask import Flask, Response, request

SHARED_SECRET = "JBSWY3DPEHPK3PXP"
EPOCH = 30
TOTP = pyotp.TOTP(SHARED_SECRET)

RATE_LIMIT = 100
RATE_WINDOW = 10
BAN_DURATION = 60

request_log = defaultdict(lambda: deque())
rate_banned = {}
lock = threading.Lock()

def rate_check(ip: str) -> bool:
    now = time.time()
    with lock:
        if ip in rate_banned:
            if now < rate_banned[ip]:
                return False
            del rate_banned[ip]
        dq = request_log[ip]
        while dq and dq[0] < now - RATE_WINDOW:
            dq.popleft()
        if len(dq) >= RATE_LIMIT:
            rate_banned[ip] = now + BAN_DURATION
            return False
        dq.append(now)
        return True

app = Flask(__name__)

def port_for_epoch(ts: int) -> int:
    return 8000 + (int(TOTP.at(ts)) % 50)

def candidate_ports():
    now = int(time.time())
    return [port_for_epoch(now), port_for_epoch(now - EPOCH), port_for_epoch(now + EPOCH)]

@app.route("/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
def proxy(path):
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if not rate_check(ip):
        return Response('{"error": "rate limit exceeded"}', status=429, content_type="application/json")

    headers = {k: v for k, v in request.headers if k.lower() != "host"}
    headers["X-Forwarded-For"] = ip

    for attempt in range(6):
        for port in (candidate_ports() if attempt == 0 else candidate_ports()):
            try:
                r = requests.request(
                    request.method, f"http://127.0.0.1:{port}/{path}",
                    params=request.args, data=request.get_data(),
                    headers=headers, timeout=2)
                if r.status_code == 403:
                    continue
                return Response(r.content, status=r.status_code, content_type=r.headers.get("Content-Type", "text/plain"))
            except requests.RequestException:
                continue
        time.sleep(0.5)

    return Response("<h1>Forbidden</h1><address>Microsoft-IIS/10.0</address>", status=403, headers={"Server": "Microsoft-IIS/10.0"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
