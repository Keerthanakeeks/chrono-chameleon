from flask import Flask
import os
app = Flask(__name__)
PORT = os.environ.get('PORT', '8000') 
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def home(path):
    return f"🟢 SECURE CONNECTION: You are connected to the Real App on Port {PORT}!"
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(PORT))
