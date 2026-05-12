-- Setup iniziale: crea il database e l'utente applicativo.
-- Da eseguire UNA volta come root: sudo mysql < setup_db.sql

CREATE DATABASE IF NOT EXISTS maquetaweb
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'maqueta'@'localhost'
  IDENTIFIED BY 'maqueta_dev_2026';

GRANT ALL PRIVILEGES ON maquetaweb.* TO 'maqueta'@'localhost';

FLUSH PRIVILEGES;

SELECT 'Setup DB completato.' AS status;
