"""
Script per inizializzare il database MySQL.
Esegui questo script per creare le tabelle e l'utente admin di default.

Utilizzo:
    python init_db.py

Prerequisiti:
    1. MySQL deve essere in esecuzione
    2. Crea il database 'gestionale' in MySQL:
       CREATE DATABASE gestionale CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    3. Configura le credenziali in config.py se necessario
"""

from app import init_db

if __name__ == '__main__':
    print("Inizializzazione database...")
    init_db()
    print("Database inizializzato con successo!")
    print("\nCredenziali admin di default:")
    print("  Username: admin")
    print("  Password: admin123")
    print("\nATTENZIONE: Cambia la password dell'admin dopo il primo accesso!")
