-- Migrazione: Aggiunta categorie servizi
-- Eseguire questo script su un database esistente

-- Tabella categorie servizi
CREATE TABLE IF NOT EXISTS categorie_servizi (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    descrizione VARCHAR(300),
    icona VARCHAR(50) DEFAULT 'bi-folder',
    ordine INT DEFAULT 0,
    attivo BOOLEAN DEFAULT TRUE,
    data_creazione DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Aggiunta colonna categoria_id alla tabella servizi
ALTER TABLE servizi ADD COLUMN IF NOT EXISTS categoria_id INT NULL;
ALTER TABLE servizi ADD FOREIGN KEY (categoria_id) REFERENCES categorie_servizi(id) ON DELETE SET NULL;

-- Aggiunta voce menu per Categorie Servizi
INSERT INTO menu (nome, icona, url, ordine, attivo) VALUES
('Categorie Servizi', 'bi-folder', '/admin/categorie-servizi', 4, TRUE);
