import os

# Carica variabili d'ambiente da .env se python-dotenv e` installato.
# E` opzionale: se non c'e`, vengono usati i default hardcoded sotto
# (utile per esecuzioni rapide senza configurazione).
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
except ImportError:
    pass


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'chiave-segreta-cambiami-in-produzione'

    # Configurazione MySQL
    MYSQL_HOST = os.environ.get('MYSQL_HOST') or 'localhost'
    MYSQL_USER = os.environ.get('MYSQL_USER') or 'tuoutente'
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD') or 'tuapassword'
    MYSQL_DB = os.environ.get('MYSQL_DB') or 'maquetaweb'

    # Configurazione Upload
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # Cartella di staging per gli upload differiti verso il NAS.
    # I file caricati dagli utenti vengono salvati qui in modo veloce e
    # poi trasferiti al NAS in background dal worker di upload_queue.
    STAGING_FOLDER = os.environ.get('STAGING_FOLDER') or \
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'staging')

    # Worker della coda upload NAS
    UPLOAD_WORKER_INTERVAL = float(os.environ.get('UPLOAD_WORKER_INTERVAL') or 2.0)  # secondi tra un ciclo e l'altro
    UPLOAD_MAX_ATTEMPTS = int(os.environ.get('UPLOAD_MAX_ATTEMPTS') or 5)

    # Configurazione NAS (SFTP)
    NAS_HOST = os.environ.get('NAS_HOST') or '93.49.81.244'
    NAS_PORT = int(os.environ.get('NAS_PORT') or 22)
    NAS_USER = os.environ.get('NAS_USER') or 'Blackdog'
    NAS_PASSWORD = os.environ.get('NAS_PASSWORD') or '$MqtServ2025'
    NAS_BASE_PATH = os.environ.get('NAS_BASE_PATH') or 'applicazione/MaquetaFiles'
