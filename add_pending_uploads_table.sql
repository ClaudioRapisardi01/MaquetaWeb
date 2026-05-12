-- Coda di upload differiti verso il NAS.
-- Il file viene salvato subito in STAGING_FOLDER (locale) e questa riga
-- viene creata con status='pending'. Il worker in background pesca le
-- righe pending, le invia via SFTP e cancella il file locale a successo.

USE maquetaweb;

CREATE TABLE IF NOT EXISTS pending_uploads (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    subpath VARCHAR(500) NOT NULL DEFAULT '',
    filename VARCHAR(500) NOT NULL,
    local_path VARCHAR(1000) NOT NULL,
    size_bytes BIGINT NOT NULL DEFAULT 0,
    status ENUM('pending', 'uploading', 'uploaded', 'failed') NOT NULL DEFAULT 'pending',
    attempts INT NOT NULL DEFAULT 0,
    error_message TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_user_path (username, subpath)
);
