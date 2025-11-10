from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Tabella associativa per artisti e dischi (molti a molti)
artisti_dischi = db.Table('artisti_dischi',
    db.Column('artista_id', db.Integer, db.ForeignKey('artisti.id'), primary_key=True),
    db.Column('disco_id', db.Integer, db.ForeignKey('dischi.id'), primary_key=True)
)

# Tabella associativa per artisti e singoli (molti a molti)
artisti_singoli = db.Table('artisti_singoli',
    db.Column('artista_id', db.Integer, db.ForeignKey('artisti.id'), primary_key=True),
    db.Column('singolo_id', db.Integer, db.ForeignKey('singoli.id'), primary_key=True)
)

# Tabella associativa per ruoli e permessi (molti a molti)
ruoli_permessi = db.Table('ruoli_permessi',
    db.Column('ruolo_id', db.Integer, db.ForeignKey('ruoli.id'), primary_key=True),
    db.Column('permesso_id', db.Integer, db.ForeignKey('permessi.id'), primary_key=True)
)


class Permesso(db.Model):
    __tablename__ = 'permessi'

    id = db.Column(db.Integer, primary_key=True)
    codice = db.Column(db.String(50), unique=True, nullable=False)  # es. artisti.create, artisti.read, artisti.update, artisti.delete
    nome = db.Column(db.String(100), nullable=False)
    descrizione = db.Column(db.String(255))
    modulo = db.Column(db.String(50))  # artisti, dischi, singoli, eventi, etc.

    def __repr__(self):
        return f'<Permesso {self.codice}>'


class Ruolo(db.Model):
    __tablename__ = 'ruoli'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)
    descrizione = db.Column(db.String(255))
    is_system = db.Column(db.Boolean, default=False)  # True per ruoli di sistema (admin, editor, user)
    data_creazione = db.Column(db.DateTime, default=datetime.utcnow)

    # Relazioni
    permessi = db.relationship('Permesso', secondary=ruoli_permessi, backref=db.backref('ruoli', lazy='dynamic'))

    def ha_permesso(self, codice_permesso):
        """Controlla se il ruolo ha un permesso specifico"""
        return any(p.codice == codice_permesso for p in self.permessi)

    def __repr__(self):
        return f'<Ruolo {self.nome}>'


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    ruolo = db.Column(db.String(20), nullable=False, default='user')  # Manteniamo per retrocompatibilità
    ruolo_id = db.Column(db.Integer, db.ForeignKey('ruoli.id'))  # Nuovo sistema ruoli
    attivo = db.Column(db.Boolean, default=True)
    data_creazione = db.Column(db.DateTime, default=datetime.utcnow)

    # Relazioni
    ruolo_custom = db.relationship('Ruolo', backref='utenti')
    artisti = db.relationship('Artista', backref='creatore', lazy=True, foreign_keys='Artista.creato_da')
    dischi = db.relationship('Disco', backref='creatore', lazy=True, foreign_keys='Disco.creato_da')
    singoli = db.relationship('Singolo', backref='creatore', lazy=True, foreign_keys='Singolo.creato_da')
    eventi = db.relationship('Evento', backref='creatore', lazy=True, foreign_keys='Evento.creato_da')
    documenti = db.relationship('Documento', backref='caricatore', lazy=True, foreign_keys='Documento.caricato_da')
    news = db.relationship('News', backref='autore', lazy=True, foreign_keys='News.creato_da')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        # Controlla sia il vecchio sistema che il nuovo
        if self.ruolo == 'admin':
            return True
        if self.ruolo_custom and self.ruolo_custom.nome == 'admin':
            return True
        return False

    def is_editor(self):
        # Controlla sia il vecchio sistema che il nuovo
        if self.ruolo in ['admin', 'editor']:
            return True
        if self.ruolo_custom and self.ruolo_custom.nome in ['admin', 'editor']:
            return True
        return False

    def ha_permesso(self, codice_permesso):
        """Controlla se l'utente ha un permesso specifico"""
        # Admin ha sempre tutti i permessi
        if self.is_admin():
            return True
        # Se ha un ruolo custom, controlla i permessi del ruolo
        if self.ruolo_custom:
            return self.ruolo_custom.ha_permesso(codice_permesso)
        # Fallback per vecchio sistema
        if self.is_editor() and any(x in codice_permesso for x in ['read', 'create', 'update']):
            return True
        if codice_permesso.endswith('.read'):
            return True
        return False

    def get_permessi(self):
        """Restituisce tutti i permessi dell'utente"""
        if self.is_admin():
            return Permesso.query.all()
        if self.ruolo_custom:
            return self.ruolo_custom.permessi
        return []

    def __repr__(self):
        return f'<User {self.username}>'


class Artista(db.Model):
    __tablename__ = 'artisti'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    nome_arte = db.Column(db.String(100), nullable=False, unique=True)
    biografia = db.Column(db.Text)
    genere_musicale = db.Column(db.String(50))
    foto = db.Column(db.String(255))
    data_nascita = db.Column(db.Date)
    paese = db.Column(db.String(50))
    sito_web = db.Column(db.String(200))
    social_instagram = db.Column(db.String(200))
    social_facebook = db.Column(db.String(200))
    social_twitter = db.Column(db.String(200))
    social_spotify = db.Column(db.String(200))
    attivo = db.Column(db.Boolean, default=True)
    data_creazione = db.Column(db.DateTime, default=datetime.utcnow)
    creato_da = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relazioni
    dischi = db.relationship('Disco', secondary=artisti_dischi, backref=db.backref('artisti', lazy='dynamic'))
    singoli = db.relationship('Singolo', secondary=artisti_singoli, backref=db.backref('artisti', lazy='dynamic'))

    def __repr__(self):
        return f'<Artista {self.nome_arte}>'


class Disco(db.Model):
    __tablename__ = 'dischi'

    id = db.Column(db.Integer, primary_key=True)
    titolo = db.Column(db.String(200), nullable=False)
    descrizione = db.Column(db.Text)
    data_uscita = db.Column(db.Date)
    copertina = db.Column(db.String(255))
    etichetta = db.Column(db.String(100))
    numero_tracce = db.Column(db.Integer)
    genere = db.Column(db.String(50))
    formato = db.Column(db.String(50))  # CD, Vinile, Digitale
    codice_catalogo = db.Column(db.String(50), unique=True)
    link_spotify = db.Column(db.String(200))
    link_apple_music = db.Column(db.String(200))
    link_youtube = db.Column(db.String(200))
    data_creazione = db.Column(db.DateTime, default=datetime.utcnow)
    creato_da = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f'<Disco {self.titolo}>'


class Singolo(db.Model):
    __tablename__ = 'singoli'

    id = db.Column(db.Integer, primary_key=True)
    titolo = db.Column(db.String(200), nullable=False)
    descrizione = db.Column(db.Text)
    data_uscita = db.Column(db.Date)
    copertina = db.Column(db.String(255))
    durata = db.Column(db.String(20))  # Formato MM:SS
    genere = db.Column(db.String(50))
    etichetta = db.Column(db.String(100))
    isrc = db.Column(db.String(50), unique=True)  # International Standard Recording Code
    link_spotify = db.Column(db.String(200))
    link_apple_music = db.Column(db.String(200))
    link_youtube = db.Column(db.String(200))
    data_creazione = db.Column(db.DateTime, default=datetime.utcnow)
    creato_da = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f'<Singolo {self.titolo}>'


class Evento(db.Model):
    __tablename__ = 'eventi'

    id = db.Column(db.Integer, primary_key=True)
    titolo = db.Column(db.String(200), nullable=False)
    descrizione = db.Column(db.Text)
    tipo = db.Column(db.String(50))  # Concerto, Registrazione, Riunione, etc.
    data_inizio = db.Column(db.DateTime, nullable=False)
    data_fine = db.Column(db.DateTime)
    luogo = db.Column(db.String(200))
    indirizzo = db.Column(db.String(300))
    citta = db.Column(db.String(100))
    paese = db.Column(db.String(50))
    visibilita = db.Column(db.String(20), default='privato')  # pubblico, privato
    note = db.Column(db.Text)
    data_creazione = db.Column(db.DateTime, default=datetime.utcnow)
    creato_da = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f'<Evento {self.titolo}>'


class Servizio(db.Model):
    __tablename__ = 'servizi'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descrizione = db.Column(db.Text)
    categoria = db.Column(db.String(50))  # Produzione, Distribuzione, Marketing, etc.
    prezzo = db.Column(db.Numeric(10, 2))
    valuta = db.Column(db.String(3), default='EUR')
    durata = db.Column(db.String(50))
    attivo = db.Column(db.Boolean, default=True)
    icona = db.Column(db.String(50))  # Nome icona per UI
    data_creazione = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Servizio {self.nome}>'


class Staff(db.Model):
    __tablename__ = 'staff'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cognome = db.Column(db.String(100), nullable=False)
    ruolo = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True)
    telefono = db.Column(db.String(20))
    foto = db.Column(db.String(255))
    biografia = db.Column(db.Text)
    reparto = db.Column(db.String(50))  # A&R, Marketing, Produzione, etc.
    data_assunzione = db.Column(db.Date)
    attivo = db.Column(db.Boolean, default=True)
    data_creazione = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Staff {self.nome} {self.cognome}>'


class Documento(db.Model):
    __tablename__ = 'documenti'

    id = db.Column(db.Integer, primary_key=True)
    titolo = db.Column(db.String(200), nullable=False)
    descrizione = db.Column(db.Text)
    nome_file = db.Column(db.String(255), nullable=False)
    percorso_file = db.Column(db.String(500), nullable=False)
    tipo = db.Column(db.String(50))  # Contratto, Fattura, Report, etc.
    dimensione = db.Column(db.Integer)  # In bytes
    mime_type = db.Column(db.String(100))
    visibilita = db.Column(db.String(20), default='privato')  # pubblico, privato
    data_upload = db.Column(db.DateTime, default=datetime.utcnow)
    caricato_da = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f'<Documento {self.titolo}>'


class News(db.Model):
    __tablename__ = 'news'

    id = db.Column(db.Integer, primary_key=True)
    titolo = db.Column(db.String(200), nullable=False)
    contenuto = db.Column(db.Text, nullable=False)
    sommario = db.Column(db.String(500))
    immagine = db.Column(db.String(255))
    categoria = db.Column(db.String(50))  # Lancio, Evento, Comunicato, etc.
    tipo = db.Column(db.String(20), default='interna')  # interna, esterna
    pubblicata = db.Column(db.Boolean, default=False)
    data_pubblicazione = db.Column(db.DateTime)
    data_creazione = db.Column(db.DateTime, default=datetime.utcnow)
    data_modifica = db.Column(db.DateTime, onupdate=datetime.utcnow)
    creato_da = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f'<News {self.titolo}>'
