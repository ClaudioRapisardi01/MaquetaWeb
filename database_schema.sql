-- Database: maquetaweb
-- Creazione database
CREATE DATABASE IF NOT EXISTS maquetaweb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE maquetaweb;

-- Tabella utenti
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
);

-- Tabella menu (voci del sidemenu)
CREATE TABLE IF NOT EXISTS menu (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    icona VARCHAR(50) DEFAULT 'bi-circle',
    url VARCHAR(200) NOT NULL,
    ordine INT DEFAULT 0,
    parent_id INT NULL,
    attivo BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (parent_id) REFERENCES menu(id) ON DELETE SET NULL
);

-- Tabella permessi (relazione utenti-menu)
-- Se esiste un record per (utente_id, menu_id), l'utente può vedere quel menu
-- La semplice esistenza del record indica che l'utente ha il permesso
CREATE TABLE IF NOT EXISTS permessi (
    id INT AUTO_INCREMENT PRIMARY KEY,
    utente_id INT NOT NULL,
    menu_id INT NOT NULL,
    FOREIGN KEY (utente_id) REFERENCES utenti(id) ON DELETE CASCADE,
    FOREIGN KEY (menu_id) REFERENCES menu(id) ON DELETE CASCADE,
    UNIQUE KEY unique_permesso (utente_id, menu_id)
);

-- Tabella servizi
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
);

-- Tabella news
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
);

-- Inserimento voci menu di default
INSERT INTO menu (nome, icona, url, ordine, attivo) VALUES
('Dashboard', 'bi-speedometer2', '/dashboard', 0, TRUE),
('Utenti', 'bi-people', '/admin/utenti', 1, TRUE),
('Gestione Menu', 'bi-list-ul', '/admin/menu', 2, TRUE),
('Servizi', 'bi-briefcase', '/admin/servizi', 3, TRUE),
('News', 'bi-newspaper', '/admin/news', 4, TRUE);

-- NOTA: L'utente admin viene creato automaticamente da app.py con password: admin123
-- Gli amministratori vedono tutte le voci di menu indipendentemente dai permessi
-- Per gli utenti normali, se esiste un record in permessi per (utente_id, menu_id),
-- l'utente può vedere quella voce di menu
