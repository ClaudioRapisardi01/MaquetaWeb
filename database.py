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

    # Tabella servizi
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS servizi (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nome VARCHAR(150) NOT NULL,
            descrizione TEXT,
            descrizione_breve VARCHAR(300),
            foto VARCHAR(500),
            icona VARCHAR(50) DEFAULT 'bi-gear',
            prezzo DECIMAL(10,2) NULL,
            durata VARCHAR(50) NULL,
            attivo BOOLEAN DEFAULT TRUE,
            in_evidenza BOOLEAN DEFAULT FALSE,
            ordine INT DEFAULT 0,
            data_creazione DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabella news
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INT AUTO_INCREMENT PRIMARY KEY,
            titolo VARCHAR(255) NOT NULL,
            slug VARCHAR(255) UNIQUE,
            contenuto TEXT,
            estratto VARCHAR(500),
            immagine VARCHAR(500),
            autore_id INT,
            categoria VARCHAR(100),
            tags VARCHAR(255),
            pubblicato BOOLEAN DEFAULT FALSE,
            in_evidenza BOOLEAN DEFAULT FALSE,
            data_pubblicazione DATETIME NULL,
            data_creazione DATETIME DEFAULT CURRENT_TIMESTAMP,
            data_modifica DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            visualizzazioni INT DEFAULT 0,
            FOREIGN KEY (autore_id) REFERENCES utenti(id) ON DELETE SET NULL
        )
    ''')

    conn.commit()
    cursor.close()
    conn.close()
