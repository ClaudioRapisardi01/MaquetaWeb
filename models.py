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
    def get_all():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM menu ORDER BY ordine')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [Menu(**row) for row in rows]

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

    def delete(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM menu WHERE id = %s', (self.id,))
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


class Servizio:
    def __init__(self, id=None, nome=None, descrizione=None, descrizione_breve=None,
                 foto=None, icona='bi-gear', prezzo=None, durata=None,
                 attivo=True, in_evidenza=False, ordine=0, data_creazione=None):
        self.id = id
        self.nome = nome
        self.descrizione = descrizione
        self.descrizione_breve = descrizione_breve
        self.foto = foto
        self.icona = icona
        self.prezzo = prezzo
        self.durata = durata
        self.attivo = attivo
        self.in_evidenza = in_evidenza
        self.ordine = ordine
        self.data_creazione = data_creazione

    @staticmethod
    def get_by_id(servizio_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM servizi WHERE id = %s', (servizio_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return Servizio(**row)
        return None

    @staticmethod
    def get_all():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM servizi ORDER BY ordine, id')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [Servizio(**row) for row in rows]

    @staticmethod
    def get_all_active():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM servizi WHERE attivo = TRUE ORDER BY ordine, id')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [Servizio(**row) for row in rows]

    @staticmethod
    def get_in_evidenza():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM servizi WHERE attivo = TRUE AND in_evidenza = TRUE ORDER BY ordine, id')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [Servizio(**row) for row in rows]

    def save(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        if self.id:
            cursor.execute('''
                UPDATE servizi SET nome=%s, descrizione=%s, descrizione_breve=%s,
                foto=%s, icona=%s, prezzo=%s, durata=%s, attivo=%s, in_evidenza=%s, ordine=%s
                WHERE id=%s
            ''', (self.nome, self.descrizione, self.descrizione_breve,
                  self.foto, self.icona, self.prezzo, self.durata,
                  self.attivo, self.in_evidenza, self.ordine, self.id))
        else:
            cursor.execute('''
                INSERT INTO servizi (nome, descrizione, descrizione_breve, foto, icona, prezzo, durata, attivo, in_evidenza, ordine)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (self.nome, self.descrizione, self.descrizione_breve,
                  self.foto, self.icona, self.prezzo, self.durata,
                  self.attivo, self.in_evidenza, self.ordine))
            self.id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()

    def delete(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM servizi WHERE id = %s', (self.id,))
        conn.commit()
        cursor.close()
        conn.close()


class News:
    def __init__(self, id=None, titolo=None, slug=None, contenuto=None, estratto=None,
                 immagine=None, autore_id=None, categoria=None, tags=None,
                 pubblicato=False, in_evidenza=False, data_pubblicazione=None,
                 data_creazione=None, data_modifica=None, visualizzazioni=0):
        self.id = id
        self.titolo = titolo
        self.slug = slug
        self.contenuto = contenuto
        self.estratto = estratto
        self.immagine = immagine
        self.autore_id = autore_id
        self.categoria = categoria
        self.tags = tags
        self.pubblicato = pubblicato
        self.in_evidenza = in_evidenza
        self.data_pubblicazione = data_pubblicazione
        self.data_creazione = data_creazione
        self.data_modifica = data_modifica
        self.visualizzazioni = visualizzazioni

    @staticmethod
    def get_by_id(news_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM news WHERE id = %s', (news_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return News(**row)
        return None

    @staticmethod
    def get_by_slug(slug):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM news WHERE slug = %s', (slug,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return News(**row)
        return None

    @staticmethod
    def get_all():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM news ORDER BY data_creazione DESC')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [News(**row) for row in rows]

    @staticmethod
    def get_all_published():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM news
            WHERE pubblicato = TRUE AND (data_pubblicazione IS NULL OR data_pubblicazione <= NOW())
            ORDER BY data_pubblicazione DESC, data_creazione DESC
        ''')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [News(**row) for row in rows]

    @staticmethod
    def get_in_evidenza():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM news
            WHERE pubblicato = TRUE AND in_evidenza = TRUE
            AND (data_pubblicazione IS NULL OR data_pubblicazione <= NOW())
            ORDER BY data_pubblicazione DESC, data_creazione DESC
        ''')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [News(**row) for row in rows]

    @staticmethod
    def get_by_categoria(categoria):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM news
            WHERE pubblicato = TRUE AND categoria = %s
            AND (data_pubblicazione IS NULL OR data_pubblicazione <= NOW())
            ORDER BY data_pubblicazione DESC
        ''', (categoria,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [News(**row) for row in rows]

    def get_autore(self):
        """Restituisce l'oggetto Utente dell'autore."""
        if self.autore_id:
            return Utente.get_by_id(self.autore_id)
        return None

    def save(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        if self.id:
            cursor.execute('''
                UPDATE news SET titolo=%s, slug=%s, contenuto=%s, estratto=%s,
                immagine=%s, autore_id=%s, categoria=%s, tags=%s, pubblicato=%s,
                in_evidenza=%s, data_pubblicazione=%s, data_modifica=NOW()
                WHERE id=%s
            ''', (self.titolo, self.slug, self.contenuto, self.estratto,
                  self.immagine, self.autore_id, self.categoria, self.tags,
                  self.pubblicato, self.in_evidenza, self.data_pubblicazione, self.id))
        else:
            cursor.execute('''
                INSERT INTO news (titolo, slug, contenuto, estratto, immagine, autore_id,
                categoria, tags, pubblicato, in_evidenza, data_pubblicazione)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (self.titolo, self.slug, self.contenuto, self.estratto,
                  self.immagine, self.autore_id, self.categoria, self.tags,
                  self.pubblicato, self.in_evidenza, self.data_pubblicazione))
            self.id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()

    def delete(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM news WHERE id = %s', (self.id,))
        conn.commit()
        cursor.close()
        conn.close()

    def incrementa_visualizzazioni(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE news SET visualizzazioni = visualizzazioni + 1 WHERE id = %s', (self.id,))
        conn.commit()
        cursor.close()
        conn.close()
        self.visualizzazioni += 1
