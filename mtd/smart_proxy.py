import time

import pyotp
import requests
from flask import Flask, Response, request

SHARED_SECRET = "JBSWY3DPEHPK3PXP"
EPOCH = 30
TOTP = pyotp.TOTP(SHARED_SECRET)
app = Flask(__name__)


def port_for_epoch(ts: int) -> int:
    return 8000 + (int(TOTP.at(ts)) % 50)


def candidate_ports():
    now = int(time.time())
    return [port_for_epoch(now),
            port_for_epoch(now - EPOCH),
            port_for_epoch(now + EPOCH)]


@app.route("/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
def proxy(path):
    headers = {k: v for k, v in request.headers if k.lower() != "host"}
    headers["X-Forwarded-For"] = request.remote_addr
    attempts = candidate_ports()
    for attempt in range(6):  # hold connection through the 2s shift
        for port in (attempts if attempt == 0 else candidate_ports()):
            try:
                r = requests.request(
                    request.method,
                    f"http://127.0.0.1:{port}/{path}",
                    params=request.args,
                    data=request.get_data(),
                    headers=headers,
                    timeout=2,
                )
                if r.status_code == 403:
                    continue  # honeypot answered; wrong port
                return Response(r.content, status=r.status_code,
                                content_type=r.headers.get("Content-Type", "text/plain"))
            except requests.RequestException:
                continue
        time.sleep(0.5)
    return Response("<h1>Forbidden</h1><address>Microsoft-IIS/10.0</address>",
                    status=403, headers={"Server": "Microsoft-IIS/10.0"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
