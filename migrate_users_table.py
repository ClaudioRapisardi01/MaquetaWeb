import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

# Parse DATABASE_URI
DATABASE_URI = os.getenv('DATABASE_URI', 'mysql+pymysql://root@localhost/discografica_db')
uri_parts = DATABASE_URI.replace('mysql+pymysql://', '').split('@')
credentials = uri_parts[0].split(':')
username = credentials[0]
password = credentials[1] if len(credentials) > 1 else ''
host_db = uri_parts[1].split('/')
host = host_db[0]
database = host_db[1] if len(host_db) > 1 else 'discografica_db'

print("=" * 60)
print("MIGRAZIONE TABELLA USERS")
print("=" * 60)

try:
    # Connetti al database
    connection = pymysql.connect(
        host=host,
        user=username,
        password=password,
        database=database,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

    with connection.cursor() as cursor:
        # Aggiungi la colonna ruolo_id se non esiste
        print("\nAggiunta colonna ruolo_id alla tabella users...")
        try:
            cursor.execute("""
                ALTER TABLE users
                ADD COLUMN ruolo_id INT NULL AFTER ruolo,
                ADD CONSTRAINT fk_users_ruolo
                FOREIGN KEY (ruolo_id) REFERENCES ruoli(id)
            """)
            connection.commit()
            print("OK - Colonna ruolo_id aggiunta con successo!")
        except pymysql.err.OperationalError as e:
            if "Duplicate column name" in str(e):
                print("  - Colonna ruolo_id già esistente, skip")
            else:
                raise

    connection.close()
    print("\n" + "=" * 60)
    print("MIGRAZIONE COMPLETATA!")
    print("=" * 60)
    print("\nOra puoi eseguire: python init_permissions.py")

except Exception as e:
    print(f"\nERRORE durante la migrazione: {e}")
    raise
