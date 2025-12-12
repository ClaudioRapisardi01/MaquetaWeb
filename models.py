from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection

class Utente:
    def __init__(self, id=None, username=None, password_hash=None, nome=None,
                 cognome=None, email=None, is_admin=False, attivo=True,
                 data_creazione=None, ultimo_accesso=None):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.nome = nome
        self.cognome = cognome
        self.email = email
        self.is_admin = is_admin
        self.attivo = attivo
        self.data_creazione = data_creazione
        self.ultimo_accesso = ultimo_accesso

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return self.attivo

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    @property
    def nome_completo(self):
        return f"{self.nome} {self.cognome}"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def get_by_id(user_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM utenti WHERE id = %s', (user_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return Utente(**row)
        return None

    @staticmethod
    def get_by_username(username):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM utenti WHERE username = %s', (username,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return Utente(**row)
        return None

    @staticmethod
    def get_by_email(email):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM utenti WHERE email = %s', (email,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return Utente(**row)
        return None

    @staticmethod
    def get_all():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM utenti ORDER BY id')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [Utente(**row) for row in rows]

    def save(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        if self.id:
            cursor.execute('''
                UPDATE utenti SET username=%s, password_hash=%s, nome=%s, cognome=%s,
                email=%s, is_admin=%s, attivo=%s, ultimo_accesso=%s WHERE id=%s
            ''', (self.username, self.password_hash, self.nome, self.cognome,
                  self.email, self.is_admin, self.attivo, self.ultimo_accesso, self.id))
        else:
            cursor.execute('''
                INSERT INTO utenti (username, password_hash, nome, cognome, email, is_admin, attivo)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (self.username, self.password_hash, self.nome, self.cognome,
                  self.email, self.is_admin, self.attivo))
            self.id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()

    def delete(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM utenti WHERE id = %s', (self.id,))
        conn.commit()
        cursor.close()
        conn.close()

    def get_menu_visibili(self):
        """Restituisce i menu visibili per l'utente."""
        conn = get_db_connection()
        cursor = conn.cursor()
        if self.is_admin:
            # Admin vede tutti i menu attivi
            cursor.execute('SELECT * FROM menu WHERE attivo = TRUE ORDER BY ordine')
        else:
            # Utente normale vede solo i menu per cui ha il permesso
            cursor.execute('''
                SELECT m.* FROM menu m
                INNER JOIN permessi p ON m.id = p.menu_id
                WHERE p.utente_id = %s AND m.attivo = TRUE
                ORDER BY m.ordine
            ''', (self.id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [Menu(**row) for row in rows]


class Menu:
    def __init__(self, id=None, nome=None, icona='bi-circle', url=None,
                 ordine=0, parent_id=None, attivo=True):
        self.id = id
        self.nome = nome
        self.icona = icona
        self.url = url
        self.ordine = ordine
        self.parent_id = parent_id
        self.attivo = attivo

    @staticmethod
    def get_by_id(menu_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM menu WHERE id = %s', (menu_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return Menu(**row)
        return None

    @staticmethod
    def get_all_active():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM menu WHERE attivo = TRUE ORDER BY ordine')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [Menu(**row) for row in rows]

    def save(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        if self.id:
            cursor.execute('''
                UPDATE menu SET nome=%s, icona=%s, url=%s, ordine=%s, parent_id=%s, attivo=%s
                WHERE id=%s
            ''', (self.nome, self.icona, self.url, self.ordine, self.parent_id, self.attivo, self.id))
        else:
            cursor.execute('''
                INSERT INTO menu (nome, icona, url, ordine, parent_id, attivo)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (self.nome, self.icona, self.url, self.ordine, self.parent_id, self.attivo))
            self.id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()


class Permesso:
    """
    Gestisce i permessi utente-menu.
    Se esiste un record per (utente_id, menu_id), l'utente può vedere quel menu.
    """

    @staticmethod
    def get_menu_ids_by_utente(utente_id):
        """Restituisce la lista degli ID menu visibili per l'utente."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT menu_id FROM permessi WHERE utente_id = %s', (utente_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [row['menu_id'] for row in rows]

    @staticmethod
    def ha_permesso(utente_id, menu_id):
        """Verifica se l'utente ha il permesso per un menu specifico."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT COUNT(*) as cnt FROM permessi WHERE utente_id = %s AND menu_id = %s',
            (utente_id, menu_id)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row['cnt'] > 0

    @staticmethod
    def aggiungi_permesso(utente_id, menu_id):
        """Aggiunge un permesso per l'utente su un menu."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT IGNORE INTO permessi (utente_id, menu_id)
            VALUES (%s, %s)
        ''', (utente_id, menu_id))
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def rimuovi_permesso(utente_id, menu_id):
        """Rimuove un permesso per l'utente su un menu."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'DELETE FROM permessi WHERE utente_id = %s AND menu_id = %s',
            (utente_id, menu_id)
        )
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def elimina_tutti_permessi_utente(utente_id):
        """Elimina tutti i permessi di un utente."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM permessi WHERE utente_id = %s', (utente_id,))
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def aggiorna_permessi_utente(utente_id, menu_ids):
        """
        Aggiorna tutti i permessi di un utente.
        Rimuove i permessi esistenti e aggiunge quelli nuovi.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        # Elimina tutti i permessi esistenti
        cursor.execute('DELETE FROM permessi WHERE utente_id = %s', (utente_id,))

        # Aggiungi i nuovi permessi
        for menu_id in menu_ids:
            cursor.execute(
                'INSERT INTO permessi (utente_id, menu_id) VALUES (%s, %s)',
                (utente_id, menu_id)
            )

        conn.commit()
        cursor.close()
        conn.close()
