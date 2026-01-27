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


class Artista:
    def __init__(self, id=None, nome=None, nome_arte=None, slug=None, bio=None,
                 foto=None, foto_copertina=None, is_band=False,
                 instagram=None, facebook=None, twitter=None, spotify=None,
                 youtube=None, apple_music=None, website=None,
                 genere=None, anno_fondazione=None, paese=None, citta=None,
                 attivo=True, in_evidenza=False, ordine=0,
                 data_creazione=None, data_modifica=None):
        self.id = id
        self.nome = nome
        self.nome_arte = nome_arte
        self.slug = slug
        self.bio = bio
        self.foto = foto
        self.foto_copertina = foto_copertina
        self.is_band = is_band
        self.instagram = instagram
        self.facebook = facebook
        self.twitter = twitter
        self.spotify = spotify
        self.youtube = youtube
        self.apple_music = apple_music
        self.website = website
        self.genere = genere
        self.anno_fondazione = anno_fondazione
        self.paese = paese
        self.citta = citta
        self.attivo = attivo
        self.in_evidenza = in_evidenza
        self.ordine = ordine
        self.data_creazione = data_creazione
        self.data_modifica = data_modifica

    @property
    def nome_display(self):
        return self.nome_arte or self.nome

    @property
    def tipo_display(self):
        return 'Band' if self.is_band else 'Solista'

    @staticmethod
    def get_by_id(artista_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM artisti WHERE id = %s', (artista_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return Artista(**row)
        return None

    @staticmethod
    def get_by_slug(slug):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM artisti WHERE slug = %s', (slug,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return Artista(**row)
        return None

    @staticmethod
    def get_all():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM artisti ORDER BY ordine, nome')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [Artista(**row) for row in rows]

    @staticmethod
    def get_all_active():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM artisti WHERE attivo = TRUE ORDER BY ordine, nome')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [Artista(**row) for row in rows]

    @staticmethod
    def get_in_evidenza():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM artisti
            WHERE attivo = TRUE AND in_evidenza = TRUE
            ORDER BY ordine, nome
        ''')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [Artista(**row) for row in rows]

    @staticmethod
    def count_stats():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT
                COUNT(*) as totali,
                SUM(attivo = TRUE) as attivi,
                SUM(in_evidenza = TRUE) as in_evidenza,
                SUM(is_band = TRUE) as band,
                SUM(is_band = FALSE) as solisti
            FROM artisti
        ''')
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row

    def get_membri(self):
        if not self.is_band:
            return []
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM membri_band
            WHERE artista_id = %s
            ORDER BY ordine, nome
        ''', (self.id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [MembroBand(**row) for row in rows]

    def get_membri_attivi(self):
        if not self.is_band:
            return []
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM membri_band
            WHERE artista_id = %s AND attivo = TRUE
            ORDER BY ordine, nome
        ''', (self.id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [MembroBand(**row) for row in rows]

    def get_dischi(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM dischi
            WHERE artista_id = %s
            ORDER BY anno_uscita DESC, data_uscita DESC
        ''', (self.id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [Disco(**row) for row in rows]

    def get_brani(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM brani
            WHERE artista_id = %s
            ORDER BY anno DESC, titolo
        ''', (self.id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [Brano(**row) for row in rows]

    def get_eventi(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM eventi
            WHERE artista_id = %s
            ORDER BY data_evento DESC
        ''', (self.id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [Evento(**row) for row in rows]

    def get_eventi_futuri(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM eventi
            WHERE artista_id = %s
            AND pubblicato = TRUE
            AND data_evento >= CURDATE()
            AND stato NOT IN ('annullato', 'concluso')
            ORDER BY data_evento ASC
        ''', (self.id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [Evento(**row) for row in rows]

    def count_dischi(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as cnt FROM dischi WHERE artista_id = %s', (self.id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row['cnt']

    def count_brani(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as cnt FROM brani WHERE artista_id = %s', (self.id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row['cnt']

    def count_eventi(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as cnt FROM eventi WHERE artista_id = %s', (self.id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row['cnt']

    def save(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        if self.id:
            cursor.execute('''
                UPDATE artisti SET
                    nome=%s, nome_arte=%s, slug=%s, bio=%s, foto=%s, foto_copertina=%s,
                    is_band=%s, instagram=%s, facebook=%s, twitter=%s, spotify=%s,
                    youtube=%s, apple_music=%s, website=%s, genere=%s, anno_fondazione=%s,
                    paese=%s, citta=%s, attivo=%s, in_evidenza=%s, ordine=%s
                WHERE id=%s
            ''', (self.nome, self.nome_arte, self.slug, self.bio, self.foto, self.foto_copertina,
                  self.is_band, self.instagram, self.facebook, self.twitter, self.spotify,
                  self.youtube, self.apple_music, self.website, self.genere, self.anno_fondazione,
                  self.paese, self.citta, self.attivo, self.in_evidenza, self.ordine, self.id))
        else:
            cursor.execute('''
                INSERT INTO artisti (nome, nome_arte, slug, bio, foto, foto_copertina,
                    is_band, instagram, facebook, twitter, spotify, youtube, apple_music,
                    website, genere, anno_fondazione, paese, citta, attivo, in_evidenza, ordine)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (self.nome, self.nome_arte, self.slug, self.bio, self.foto, self.foto_copertina,
                  self.is_band, self.instagram, self.facebook, self.twitter, self.spotify,
                  self.youtube, self.apple_music, self.website, self.genere, self.anno_fondazione,
                  self.paese, self.citta, self.attivo, self.in_evidenza, self.ordine))
            self.id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()

    def delete(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM artisti WHERE id = %s', (self.id,))
        conn.commit()
        cursor.close()
        conn.close()


class MembroBand:
    def __init__(self, id=None, artista_id=None, nome=None, cognome=None,
                 nome_arte=None, ruolo=None, foto=None, bio_breve=None,
                 attivo=True, data_ingresso=None, data_uscita=None, ordine=0,
                 data_creazione=None):
        self.id = id
        self.artista_id = artista_id
        self.nome = nome
        self.cognome = cognome
        self.nome_arte = nome_arte
        self.ruolo = ruolo
        self.foto = foto
        self.bio_breve = bio_breve
        self.attivo = attivo
        self.data_ingresso = data_ingresso
        self.data_uscita = data_uscita
        self.ordine = ordine
        self.data_creazione = data_creazione

    @property
    def nome_completo(self):
        if self.cognome:
            return f"{self.nome} {self.cognome}"
        return self.nome

    @property
    def nome_display(self):
        return self.nome_arte or self.nome_completo

    @staticmethod
    def get_by_id(membro_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM membri_band WHERE id = %s', (membro_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return MembroBand(**row)
        return None

    @staticmethod
    def get_by_artista(artista_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM membri_band
            WHERE artista_id = %s
            ORDER BY ordine, nome
        ''', (artista_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [MembroBand(**row) for row in rows]

    def get_artista(self):
        return Artista.get_by_id(self.artista_id)

    def save(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        if self.id:
            cursor.execute('''
                UPDATE membri_band SET
                    artista_id=%s, nome=%s, cognome=%s, nome_arte=%s, ruolo=%s,
                    foto=%s, bio_breve=%s, attivo=%s, data_ingresso=%s,
                    data_uscita=%s, ordine=%s
                WHERE id=%s
            ''', (self.artista_id, self.nome, self.cognome, self.nome_arte, self.ruolo,
                  self.foto, self.bio_breve, self.attivo, self.data_ingresso,
                  self.data_uscita, self.ordine, self.id))
        else:
            cursor.execute('''
                INSERT INTO membri_band (artista_id, nome, cognome, nome_arte, ruolo,
                    foto, bio_breve, attivo, data_ingresso, data_uscita, ordine)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (self.artista_id, self.nome, self.cognome, self.nome_arte, self.ruolo,
                  self.foto, self.bio_breve, self.attivo, self.data_ingresso,
                  self.data_uscita, self.ordine))
            self.id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()

    def delete(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM membri_band WHERE id = %s', (self.id,))
        conn.commit()
        cursor.close()
        conn.close()


class Disco:
    TIPI = {
        'album': 'Album',
        'ep': 'EP',
        'singolo': 'Singolo',
        'compilation': 'Compilation',
        'live': 'Live',
        'remix': 'Remix'
    }

    def __init__(self, id=None, artista_id=None, titolo=None, slug=None,
                 tipo='album', copertina=None, anno_uscita=None, data_uscita=None,
                 etichetta=None, formato=None, descrizione=None,
                 link_spotify=None, link_apple_music=None, link_youtube_music=None,
                 link_amazon_music=None, link_deezer=None, link_tidal=None,
                 link_acquisto=None, pubblicato=False, in_evidenza=False, ordine=0,
                 data_creazione=None, data_modifica=None):
        self.id = id
        self.artista_id = artista_id
        self.titolo = titolo
        self.slug = slug
        self.tipo = tipo
        self.copertina = copertina
        self.anno_uscita = anno_uscita
        self.data_uscita = data_uscita
        self.etichetta = etichetta
        self.formato = formato
        self.descrizione = descrizione
        self.link_spotify = link_spotify
        self.link_apple_music = link_apple_music
        self.link_youtube_music = link_youtube_music
        self.link_amazon_music = link_amazon_music
        self.link_deezer = link_deezer
        self.link_tidal = link_tidal
        self.link_acquisto = link_acquisto
        self.pubblicato = pubblicato
        self.in_evidenza = in_evidenza
        self.ordine = ordine
        self.data_creazione = data_creazione
        self.data_modifica = data_modifica

    @property
    def tipo_display(self):
        return self.TIPI.get(self.tipo, self.tipo)

    @staticmethod
    def get_by_id(disco_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM dischi WHERE id = %s', (disco_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return Disco(**row)
        return None

    @staticmethod
    def get_all():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM dischi ORDER BY anno_uscita DESC, titolo')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [Disco(**row) for row in rows]

    @staticmethod
    def get_all_published():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM dischi
            WHERE pubblicato = TRUE
            ORDER BY anno_uscita DESC, data_uscita DESC
        ''')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [Disco(**row) for row in rows]

    @staticmethod
    def get_by_artista(artista_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM dischi
            WHERE artista_id = %s
            ORDER BY anno_uscita DESC
        ''', (artista_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [Disco(**row) for row in rows]

    def get_artista(self):
        return Artista.get_by_id(self.artista_id)

    def get_brani(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM brani
            WHERE disco_id = %s
            ORDER BY numero_traccia, titolo
        ''', (self.id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [Brano(**row) for row in rows]

    def count_brani(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as cnt FROM brani WHERE disco_id = %s', (self.id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row['cnt']

    def get_durata_totale(self):
        brani = self.get_brani()
        totale_secondi = 0
        for brano in brani:
            if brano.durata:
                try:
                    parti = brano.durata.split(':')
                    minuti = int(parti[0])
                    secondi = int(parti[1]) if len(parti) > 1 else 0
                    totale_secondi += minuti * 60 + secondi
                except:
                    pass
        minuti = totale_secondi // 60
        secondi = totale_secondi % 60
        return f"{minuti}:{secondi:02d}"

    def save(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        if self.id:
            cursor.execute('''
                UPDATE dischi SET
                    artista_id=%s, titolo=%s, slug=%s, tipo=%s, copertina=%s,
                    anno_uscita=%s, data_uscita=%s, etichetta=%s, formato=%s,
                    descrizione=%s, link_spotify=%s, link_apple_music=%s,
                    link_youtube_music=%s, link_amazon_music=%s, link_deezer=%s,
                    link_tidal=%s, link_acquisto=%s, pubblicato=%s, in_evidenza=%s, ordine=%s
                WHERE id=%s
            ''', (self.artista_id, self.titolo, self.slug, self.tipo, self.copertina,
                  self.anno_uscita, self.data_uscita, self.etichetta, self.formato,
                  self.descrizione, self.link_spotify, self.link_apple_music,
                  self.link_youtube_music, self.link_amazon_music, self.link_deezer,
                  self.link_tidal, self.link_acquisto, self.pubblicato, self.in_evidenza,
                  self.ordine, self.id))
        else:
            cursor.execute('''
                INSERT INTO dischi (artista_id, titolo, slug, tipo, copertina,
                    anno_uscita, data_uscita, etichetta, formato, descrizione,
                    link_spotify, link_apple_music, link_youtube_music, link_amazon_music,
                    link_deezer, link_tidal, link_acquisto, pubblicato, in_evidenza, ordine)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (self.artista_id, self.titolo, self.slug, self.tipo, self.copertina,
                  self.anno_uscita, self.data_uscita, self.etichetta, self.formato,
                  self.descrizione, self.link_spotify, self.link_apple_music,
                  self.link_youtube_music, self.link_amazon_music, self.link_deezer,
                  self.link_tidal, self.link_acquisto, self.pubblicato, self.in_evidenza, self.ordine))
            self.id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()

    def delete(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM dischi WHERE id = %s', (self.id,))
        conn.commit()
        cursor.close()
        conn.close()


class Brano:
    def __init__(self, id=None, disco_id=None, artista_id=None, titolo=None,
                 slug=None, durata=None, numero_traccia=None, featuring=None,
                 produttore=None, autori=None, genere=None, anno=None, isrc=None,
                 link_spotify=None, link_apple_music=None, link_youtube=None,
                 link_youtube_music=None, link_soundcloud=None, link_altro=None,
                 testo=None, video_ufficiale=None, pubblicato=False, is_singolo=False,
                 data_uscita=None, data_creazione=None, data_modifica=None):
        self.id = id
        self.disco_id = disco_id
        self.artista_id = artista_id
        self.titolo = titolo
        self.slug = slug
        self.durata = durata
        self.numero_traccia = numero_traccia
        self.featuring = featuring
        self.produttore = produttore
        self.autori = autori
        self.genere = genere
        self.anno = anno
        self.isrc = isrc
        self.link_spotify = link_spotify
        self.link_apple_music = link_apple_music
        self.link_youtube = link_youtube
        self.link_youtube_music = link_youtube_music
        self.link_soundcloud = link_soundcloud
        self.link_altro = link_altro
        self.testo = testo
        self.video_ufficiale = video_ufficiale
        self.pubblicato = pubblicato
        self.is_singolo = is_singolo
        self.data_uscita = data_uscita
        self.data_creazione = data_creazione
        self.data_modifica = data_modifica

    @property
    def titolo_completo(self):
        if self.featuring:
            return f"{self.titolo} (feat. {self.featuring})"
        return self.titolo

    @staticmethod
    def get_by_id(brano_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM brani WHERE id = %s', (brano_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return Brano(**row)
        return None

    @staticmethod
    def get_all():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM brani ORDER BY anno DESC, titolo')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [Brano(**row) for row in rows]

    @staticmethod
    def get_by_disco(disco_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM brani
            WHERE disco_id = %s
            ORDER BY numero_traccia
        ''', (disco_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [Brano(**row) for row in rows]

    @staticmethod
    def get_by_artista(artista_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM brani
            WHERE artista_id = %s
            ORDER BY anno DESC, titolo
        ''', (artista_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [Brano(**row) for row in rows]

    @staticmethod
    def get_singoli():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM brani
            WHERE is_singolo = TRUE AND pubblicato = TRUE
            ORDER BY data_uscita DESC, anno DESC
        ''')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [Brano(**row) for row in rows]

    def get_artista(self):
        return Artista.get_by_id(self.artista_id)

    def get_disco(self):
        if self.disco_id:
            return Disco.get_by_id(self.disco_id)
        return None

    def save(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        if self.id:
            cursor.execute('''
                UPDATE brani SET
                    disco_id=%s, artista_id=%s, titolo=%s, slug=%s, durata=%s,
                    numero_traccia=%s, featuring=%s, produttore=%s, autori=%s,
                    genere=%s, anno=%s, isrc=%s, link_spotify=%s, link_apple_music=%s,
                    link_youtube=%s, link_youtube_music=%s, link_soundcloud=%s,
                    link_altro=%s, testo=%s, video_ufficiale=%s, pubblicato=%s,
                    is_singolo=%s, data_uscita=%s
                WHERE id=%s
            ''', (self.disco_id, self.artista_id, self.titolo, self.slug, self.durata,
                  self.numero_traccia, self.featuring, self.produttore, self.autori,
                  self.genere, self.anno, self.isrc, self.link_spotify, self.link_apple_music,
                  self.link_youtube, self.link_youtube_music, self.link_soundcloud,
                  self.link_altro, self.testo, self.video_ufficiale, self.pubblicato,
                  self.is_singolo, self.data_uscita, self.id))
        else:
            cursor.execute('''
                INSERT INTO brani (disco_id, artista_id, titolo, slug, durata,
                    numero_traccia, featuring, produttore, autori, genere, anno, isrc,
                    link_spotify, link_apple_music, link_youtube, link_youtube_music,
                    link_soundcloud, link_altro, testo, video_ufficiale, pubblicato,
                    is_singolo, data_uscita)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (self.disco_id, self.artista_id, self.titolo, self.slug, self.durata,
                  self.numero_traccia, self.featuring, self.produttore, self.autori,
                  self.genere, self.anno, self.isrc, self.link_spotify, self.link_apple_music,
                  self.link_youtube, self.link_youtube_music, self.link_soundcloud,
                  self.link_altro, self.testo, self.video_ufficiale, self.pubblicato,
                  self.is_singolo, self.data_uscita))
            self.id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()

    def delete(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM brani WHERE id = %s', (self.id,))
        conn.commit()
        cursor.close()
        conn.close()


class Evento:
    TIPI = {
        'concerto': 'Concerto',
        'festival': 'Festival',
        'showcase': 'Showcase',
        'dj_set': 'DJ Set',
        'live_session': 'Live Session',
        'altro': 'Altro'
    }

    STATI = {
        'programmato': ('Programmato', 'secondary'),
        'confermato': ('Confermato', 'success'),
        'annullato': ('Annullato', 'danger'),
        'posticipato': ('Posticipato', 'warning'),
        'concluso': ('Concluso', 'dark')
    }

    def __init__(self, id=None, artista_id=None, titolo=None, slug=None,
                 tipo='concerto', descrizione=None, immagine=None,
                 data_evento=None, ora_inizio=None, ora_fine=None,
                 venue=None, citta=None, paese='Italia', indirizzo=None,
                 coordinate_gps=None, link_biglietti=None, prezzo_da=None,
                 prezzo_a=None, sold_out=False, stato='programmato',
                 pubblicato=False, in_evidenza=False,
                 data_creazione=None, data_modifica=None):
        self.id = id
        self.artista_id = artista_id
        self.titolo = titolo
        self.slug = slug
        self.tipo = tipo
        self.descrizione = descrizione
        self.immagine = immagine
        self.data_evento = data_evento
        self.ora_inizio = ora_inizio
        self.ora_fine = ora_fine
        self.venue = venue
        self.citta = citta
        self.paese = paese
        self.indirizzo = indirizzo
        self.coordinate_gps = coordinate_gps
        self.link_biglietti = link_biglietti
        self.prezzo_da = prezzo_da
        self.prezzo_a = prezzo_a
        self.sold_out = sold_out
        self.stato = stato
        self.pubblicato = pubblicato
        self.in_evidenza = in_evidenza
        self.data_creazione = data_creazione
        self.data_modifica = data_modifica

    @property
    def tipo_display(self):
        return self.TIPI.get(self.tipo, self.tipo)

    @property
    def stato_display(self):
        return self.STATI.get(self.stato, ('Sconosciuto', 'secondary'))[0]

    @property
    def stato_badge_class(self):
        return self.STATI.get(self.stato, ('Sconosciuto', 'secondary'))[1]

    @property
    def luogo_completo(self):
        parti = []
        if self.venue:
            parti.append(self.venue)
        if self.citta:
            parti.append(self.citta)
        if self.paese and self.paese != 'Italia':
            parti.append(self.paese)
        return ', '.join(parti)

    @property
    def prezzo_display(self):
        if self.prezzo_da and self.prezzo_a:
            return f"{self.prezzo_da:.2f} - {self.prezzo_a:.2f} €"
        elif self.prezzo_da:
            return f"da {self.prezzo_da:.2f} €"
        return None

    @property
    def is_passato(self):
        from datetime import date
        if self.data_evento:
            if isinstance(self.data_evento, date):
                return self.data_evento < date.today()
        return False

    @staticmethod
    def get_by_id(evento_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM eventi WHERE id = %s', (evento_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return Evento(**row)
        return None

    @staticmethod
    def get_all():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM eventi ORDER BY data_evento DESC')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [Evento(**row) for row in rows]

    @staticmethod
    def get_futuri():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM eventi
            WHERE pubblicato = TRUE
            AND data_evento >= CURDATE()
            AND stato NOT IN ('annullato', 'concluso')
            ORDER BY data_evento ASC
        ''')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [Evento(**row) for row in rows]

    @staticmethod
    def get_by_artista(artista_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM eventi
            WHERE artista_id = %s
            ORDER BY data_evento DESC
        ''', (artista_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [Evento(**row) for row in rows]

    def get_artista(self):
        return Artista.get_by_id(self.artista_id)

    def save(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        if self.id:
            cursor.execute('''
                UPDATE eventi SET
                    artista_id=%s, titolo=%s, slug=%s, tipo=%s, descrizione=%s,
                    immagine=%s, data_evento=%s, ora_inizio=%s, ora_fine=%s,
                    venue=%s, citta=%s, paese=%s, indirizzo=%s, coordinate_gps=%s,
                    link_biglietti=%s, prezzo_da=%s, prezzo_a=%s, sold_out=%s,
                    stato=%s, pubblicato=%s, in_evidenza=%s
                WHERE id=%s
            ''', (self.artista_id, self.titolo, self.slug, self.tipo, self.descrizione,
                  self.immagine, self.data_evento, self.ora_inizio, self.ora_fine,
                  self.venue, self.citta, self.paese, self.indirizzo, self.coordinate_gps,
                  self.link_biglietti, self.prezzo_da, self.prezzo_a, self.sold_out,
                  self.stato, self.pubblicato, self.in_evidenza, self.id))
        else:
            cursor.execute('''
                INSERT INTO eventi (artista_id, titolo, slug, tipo, descrizione,
                    immagine, data_evento, ora_inizio, ora_fine, venue, citta, paese,
                    indirizzo, coordinate_gps, link_biglietti, prezzo_da, prezzo_a,
                    sold_out, stato, pubblicato, in_evidenza)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (self.artista_id, self.titolo, self.slug, self.tipo, self.descrizione,
                  self.immagine, self.data_evento, self.ora_inizio, self.ora_fine,
                  self.venue, self.citta, self.paese, self.indirizzo, self.coordinate_gps,
                  self.link_biglietti, self.prezzo_da, self.prezzo_a, self.sold_out,
                  self.stato, self.pubblicato, self.in_evidenza))
            self.id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()

    def delete(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM eventi WHERE id = %s', (self.id,))
        conn.commit()
        cursor.close()
        conn.close()
