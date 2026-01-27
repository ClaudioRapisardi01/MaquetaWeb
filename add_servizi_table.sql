-- Script per aggiungere la tabella servizi al database esistente
-- Eseguire questo script se il database e gia stato creato

USE maquetaweb;

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

-- Aggiungere la voce menu per i servizi (se non esiste gia)
INSERT INTO menu (nome, icona, url, ordine, attivo)
SELECT 'Servizi', 'bi-briefcase', '/admin/servizi', 3, TRUE
WHERE NOT EXISTS (
    SELECT 1 FROM menu WHERE url = '/admin/servizi'
);
