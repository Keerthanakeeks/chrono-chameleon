"""
Honeypot Trap Service:
- Catches ALL requests, logs attacker IP + port + timestamp to attack.log
- Chameleon Effect: pure Microsoft-IIS/10.0 Server header (Werkzeug leak stripped)
"""
import os
import time

from flask import Flask, request

app = Flask(__name__)
PORT = int(os.environ.get("PORT", 8000))
LOG_PATH = "/shared_logs/attack.log"


# Chameleon fix: strip Werkzeug's automatic Server header so only
# "Microsoft-IIS/10.0" reaches the attacker — zero Python/Flask fingerprint.
class HideWerkzeug:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        def fake_start_response(status, headers, exc_info=None):
            headers = [(k, v) for k, v in headers if k.lower() != "server"]
            return start_response(status, headers, exc_info)
        return self.wsgi_app(environ, fake_start_response)


app.wsgi_app = HideWerkzeug(app.wsgi_app)


def log_attack():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    with open(LOG_PATH, "a") as f:
        f.write(f"{ip} {PORT} {time.strftime('%Y-%m-%d %H:%M:%S')}\n")


@app.route("/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "DELETE"])
@app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def trap(path):
    log_attack()
    body = (
        "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.01//EN\""
        "\"http://www.w3.org/TR/html4/strict.dtd\">"
        "<HTML><HEAD><TITLE>403 Forbidden</TITLE></HEAD><BODY>"
        "<h1>Forbidden</h1><p>You don't have permission to access this resource.</p>"
        "<hr><address>Microsoft-IIS/10.0</address></BODY></HTML>"
    )
    return body, 403, {
        "Server": "Microsoft-IIS/10.0",
        "X-Powered-By": "ASP.NET",
        "X-AspNet-Version": "4.0.30319",
        "Content-Type": "text/html; charset=utf-8",
    }


if __name__ == "__main__":
    os.makedirs("/shared_logs", exist_ok=True)
    open(LOG_PATH, "a").close()
    app.run(host="0.0.0.0", port=PORT)
