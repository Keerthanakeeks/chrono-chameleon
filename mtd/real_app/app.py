import os
from flask import Flask, jsonify

app = Flask(__name__)
PORT = int(os.environ.get("PORT", 8000))


@app.route("/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "DELETE"])
@app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def index(path):
    return jsonify({
        "status": "success",
        "message": "Real application is alive",
        "active_port": PORT,
    })


@app.route("/health")
def health():
    return jsonify({"healthy": True, "port": PORT})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
