from flask import Flask
import subprocess

app = Flask(__name__)

@app.route("/run")
def run():
    subprocess.run(["python", "vinted_scanner.py"])
    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
