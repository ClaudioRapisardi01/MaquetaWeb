import os

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

    # Configurazione NAS (SFTP)
    NAS_HOST = os.environ.get('NAS_HOST') or '93.49.81.244'
    NAS_PORT = int(os.environ.get('NAS_PORT') or 22)
    NAS_USER = os.environ.get('NAS_USER') or 'Blackdog'
    NAS_PASSWORD = os.environ.get('NAS_PASSWORD') or '$MqtServ2025'
    NAS_BASE_PATH = os.environ.get('NAS_BASE_PATH') or 'applicazione/MaquetaFiles'
