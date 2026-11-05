from flask import Flask, request, Response
import os, datetime
app = Flask(__name__)
PORT = os.environ.get('PORT', '8000')
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    attacker_ip = request.remote_addr
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open('/shared_logs/attack.log', 'a') as f:
        f.write(f"{timestamp},{attacker_ip},{PORT}\n")
    print(f"[🚨 TRAP TRIGGERED] Hacker IP {attacker_ip} caught on Port {PORT}")
    headers = {'Server': 'Microsoft-IIS/10.0', 'X-Powered-By': 'ASP.NET'}
    return Response("<html><body><h1>Access Denied</h1></body></html>", 403, headers)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(PORT))
