import subprocess
import os
import psutil
from flask import Flask, request

APP_PATH = r"C:\Users\claud\PycharmProjects\MaquetaWeb"
APP_SCRIPT = "app.py"
REQUIREMENTS = os.path.join(APP_PATH, "requirements.txt")

app = Flask(__name__)

def is_app_running():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and APP_SCRIPT in cmdline:
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def update_dependencies():
    if os.path.exists(REQUIREMENTS):
        subprocess.run(["python", "-m", "pip", "install", "-r", REQUIREMENTS], shell=True)

def restart_app():
    proc = is_app_running()
    if proc:
        proc.terminate()  # Chiude l'app se in esecuzione
    subprocess.Popen(["python", os.path.join(APP_PATH, APP_SCRIPT)], shell=True)

@app.route("/hook", methods=["POST"])
def webhook():
    # Accetta sia application/json che application/x-www-form-urlencoded
    if request.is_json:
        data = request.json
    elif request.form.get('payload'):
        import json
        data = json.loads(request.form.get('payload'))
    else:
        return "Invalid payload", 400

    if data and data.get("ref") == "refs/heads/master":  # Solo branch principale
        # Aggiorna codice
        subprocess.run(["git", "-C", APP_PATH, "pull"], shell=True)
        # Aggiorna dipendenze
        update_dependencies()
        # Riavvia o avvia app
        restart_app()
        return "Updated", 200
    return "Ignored", 200

if __name__ == "__main__":
    # All'avvio controlla se l'app è già in esecuzione, altrimenti la avvia
    restart_app()
    # Avvia server webhook
    app.run(host="0.0.0.0", port=5000)
