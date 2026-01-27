-- Script per aggiungere la tabella news al database esistente
-- Eseguire questo script se il database e gia stato creato

USE maquetaweb;

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

-- Aggiungere la voce menu per le news (se non esiste gia)
INSERT INTO menu (nome, icona, url, ordine, attivo)
SELECT 'News', 'bi-newspaper', '/admin/news', 4, TRUE
WHERE NOT EXISTS (
    SELECT 1 FROM menu WHERE url = '/admin/news'
);

-- Indice per migliorare le performance delle query sulle news pubblicate
CREATE INDEX IF NOT EXISTS idx_news_pubblicato ON news(pubblicato, data_pubblicazione);
CREATE INDEX IF NOT EXISTS idx_news_categoria ON news(categoria);
CREATE INDEX IF NOT EXISTS idx_news_slug ON news(slug);
