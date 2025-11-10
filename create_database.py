#!/usr/bin/env python
"""
Script per creare il database MySQL
"""
import pymysql
import sys

# Credenziali MySQL
MYSQL_USER = 'claudio'
MYSQL_PASSWORD = 'Superrapa22'
MYSQL_HOST = 'localhost'
DATABASE_NAME = 'discografica_db'

try:
    print("Connessione a MySQL...")
    # Connessione a MySQL senza specificare il database
    connection = pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD
    )

    cursor = connection.cursor()

    # Crea il database
    print(f"Creazione database '{DATABASE_NAME}'...")
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DATABASE_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")

    print(f"✓ Database '{DATABASE_NAME}' creato con successo!")

    cursor.close()
    connection.close()

    print("\nOra puoi eseguire: python init_db.py")

except pymysql.err.OperationalError as e:
    print(f"Errore di connessione: {e}")
    print("\nVerifica:")
    print("1. MySQL è in esecuzione?")
    print(f"2. L'utente '{MYSQL_USER}' esiste?")
    print("3. La password è corretta?")
    sys.exit(1)
except Exception as e:
    print(f"Errore: {e}")
    sys.exit(1)
