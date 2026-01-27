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

    # Tabella artisti
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS artisti (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nome VARCHAR(150) NOT NULL,
            nome_arte VARCHAR(150),
            slug VARCHAR(200) UNIQUE,
            bio TEXT,
            foto VARCHAR(500),
            foto_copertina VARCHAR(500),
            is_band BOOLEAN DEFAULT FALSE,
            instagram VARCHAR(255),
            facebook VARCHAR(255),
            twitter VARCHAR(255),
            spotify VARCHAR(255),
            youtube VARCHAR(255),
            apple_music VARCHAR(255),
            website VARCHAR(255),
            genere VARCHAR(100),
            anno_fondazione INT,
            paese VARCHAR(100),
            citta VARCHAR(100),
            attivo BOOLEAN DEFAULT TRUE,
            in_evidenza BOOLEAN DEFAULT FALSE,
            ordine INT DEFAULT 0,
            data_creazione DATETIME DEFAULT CURRENT_TIMESTAMP,
            data_modifica DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_artisti_slug (slug),
            INDEX idx_artisti_attivo (attivo),
            INDEX idx_artisti_genere (genere)
        )
    ''')

    # Tabella membri band
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS membri_band (
            id INT AUTO_INCREMENT PRIMARY KEY,
            artista_id INT NOT NULL,
            nome VARCHAR(100) NOT NULL,
            cognome VARCHAR(100),
            nome_arte VARCHAR(150),
            ruolo VARCHAR(100) NOT NULL,
            foto VARCHAR(500),
            bio_breve TEXT,
            attivo BOOLEAN DEFAULT TRUE,
            data_ingresso DATE,
            data_uscita DATE,
            ordine INT DEFAULT 0,
            data_creazione DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (artista_id) REFERENCES artisti(id) ON DELETE CASCADE,
            INDEX idx_membri_artista (artista_id),
            INDEX idx_membri_attivo (attivo)
        )
    ''')

    # Tabella dischi
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dischi (
            id INT AUTO_INCREMENT PRIMARY KEY,
            artista_id INT NOT NULL,
            titolo VARCHAR(255) NOT NULL,
            slug VARCHAR(255),
            tipo ENUM('album', 'ep', 'singolo', 'compilation', 'live', 'remix') DEFAULT 'album',
            copertina VARCHAR(500),
            anno_uscita INT,
            data_uscita DATE,
            etichetta VARCHAR(150),
            formato VARCHAR(100),
            descrizione TEXT,
            link_spotify VARCHAR(500),
            link_apple_music VARCHAR(500),
            link_youtube_music VARCHAR(500),
            link_amazon_music VARCHAR(500),
            link_deezer VARCHAR(500),
            link_tidal VARCHAR(500),
            link_acquisto VARCHAR(500),
            pubblicato BOOLEAN DEFAULT FALSE,
            in_evidenza BOOLEAN DEFAULT FALSE,
            ordine INT DEFAULT 0,
            data_creazione DATETIME DEFAULT CURRENT_TIMESTAMP,
            data_modifica DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (artista_id) REFERENCES artisti(id) ON DELETE CASCADE,
            INDEX idx_dischi_artista (artista_id),
            INDEX idx_dischi_slug (slug),
            INDEX idx_dischi_tipo (tipo),
            INDEX idx_dischi_anno (anno_uscita),
            INDEX idx_dischi_pubblicato (pubblicato)
        )
    ''')

    # Tabella brani
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS brani (
            id INT AUTO_INCREMENT PRIMARY KEY,
            disco_id INT,
            artista_id INT NOT NULL,
            titolo VARCHAR(255) NOT NULL,
            slug VARCHAR(255),
            durata VARCHAR(10),
            numero_traccia INT,
            featuring VARCHAR(255),
            produttore VARCHAR(255),
            autori VARCHAR(500),
            genere VARCHAR(100),
            anno INT,
            isrc VARCHAR(20),
            link_spotify VARCHAR(500),
            link_apple_music VARCHAR(500),
            link_youtube VARCHAR(500),
            link_youtube_music VARCHAR(500),
            link_soundcloud VARCHAR(500),
            link_altro VARCHAR(500),
            testo TEXT,
            video_ufficiale VARCHAR(500),
            pubblicato BOOLEAN DEFAULT FALSE,
            is_singolo BOOLEAN DEFAULT FALSE,
            data_uscita DATE,
            data_creazione DATETIME DEFAULT CURRENT_TIMESTAMP,
            data_modifica DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (disco_id) REFERENCES dischi(id) ON DELETE SET NULL,
            FOREIGN KEY (artista_id) REFERENCES artisti(id) ON DELETE CASCADE,
            INDEX idx_brani_disco (disco_id),
            INDEX idx_brani_artista (artista_id),
            INDEX idx_brani_pubblicato (pubblicato),
            INDEX idx_brani_numero (numero_traccia)
        )
    ''')

    # Tabella eventi
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS eventi (
            id INT AUTO_INCREMENT PRIMARY KEY,
            artista_id INT NOT NULL,
            titolo VARCHAR(255) NOT NULL,
            slug VARCHAR(255),
            tipo ENUM('concerto', 'festival', 'showcase', 'dj_set', 'live_session', 'altro') DEFAULT 'concerto',
            descrizione TEXT,
            immagine VARCHAR(500),
            data_evento DATE NOT NULL,
            ora_inizio TIME,
            ora_fine TIME,
            venue VARCHAR(200),
            citta VARCHAR(100) NOT NULL,
            paese VARCHAR(100) DEFAULT 'Italia',
            indirizzo VARCHAR(300),
            coordinate_gps VARCHAR(50),
            link_biglietti VARCHAR(500),
            prezzo_da DECIMAL(10,2),
            prezzo_a DECIMAL(10,2),
            sold_out BOOLEAN DEFAULT FALSE,
            stato ENUM('programmato', 'confermato', 'annullato', 'posticipato', 'concluso') DEFAULT 'programmato',
            pubblicato BOOLEAN DEFAULT FALSE,
            in_evidenza BOOLEAN DEFAULT FALSE,
            data_creazione DATETIME DEFAULT CURRENT_TIMESTAMP,
            data_modifica DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (artista_id) REFERENCES artisti(id) ON DELETE CASCADE,
            INDEX idx_eventi_artista (artista_id),
            INDEX idx_eventi_data (data_evento),
            INDEX idx_eventi_stato (stato),
            INDEX idx_eventi_citta (citta),
            INDEX idx_eventi_pubblicato (pubblicato)
        )
    ''')

    conn.commit()
    cursor.close()
    conn.close()
