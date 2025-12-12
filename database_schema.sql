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

-- Inserimento voci menu di default
INSERT INTO menu (nome, icona, url, ordine, attivo) VALUES
('Dashboard', 'bi-speedometer2', '/dashboard', 0, TRUE),
('Utenti', 'bi-people', '/admin/utenti', 1, TRUE);

-- NOTA: L'utente admin viene creato automaticamente da app.py con password: admin123
-- Gli amministratori vedono tutte le voci di menu indipendentemente dai permessi
-- Per gli utenti normali, se esiste un record in permessi per (utente_id, menu_id),
-- l'utente può vedere quella voce di menu
