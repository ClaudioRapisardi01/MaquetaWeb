import pymysql
from config import Config

def get_db_connection():
    """Crea e restituisce una connessione al database MySQL."""
    return pymysql.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def init_database():
    """Inizializza il database creando le tabelle necessarie."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tabella utenti
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS utenti (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            nome VARCHAR(100) NOT NULL,
            cognome VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE,
            is_admin BOOLEAN DEFAULT FALSE,
            attivo BOOLEAN DEFAULT TRUE,
            data_creazione DATETIME DEFAULT CURRENT_TIMESTAMP,
            ultimo_accesso DATETIME NULL
        )
    ''')

    # Tabella menu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS menu (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            icona VARCHAR(50) DEFAULT 'bi-circle',
            url VARCHAR(200) NOT NULL,
            ordine INT DEFAULT 0,
            parent_id INT NULL,
            attivo BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (parent_id) REFERENCES menu(id) ON DELETE SET NULL
        )
    ''')

    # Tabella permessi (semplificata: se esiste il record, l'utente può vedere il menu)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS permessi (
            id INT AUTO_INCREMENT PRIMARY KEY,
            utente_id INT NOT NULL,
            menu_id INT NOT NULL,
            FOREIGN KEY (utente_id) REFERENCES utenti(id) ON DELETE CASCADE,
            FOREIGN KEY (menu_id) REFERENCES menu(id) ON DELETE CASCADE,
            UNIQUE KEY unique_permesso (utente_id, menu_id)
        )
    ''')

    conn.commit()
    cursor.close()
    conn.close()
