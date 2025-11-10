from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, TextAreaField, SelectField, DateField, DateTimeField, BooleanField, DecimalField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, URL, ValidationError
from app.models import User, Artista, Ruolo

# ==================== AUTH FORMS ====================

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password', validators=[DataRequired()])

class RegistrazioneForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    conferma_password = PasswordField('Conferma Password', validators=[DataRequired(), EqualTo('password', message='Le password devono corrispondere')])
    ruolo = SelectField('Ruolo', choices=[('user', 'Utente'), ('editor', 'Editor'), ('admin', 'Admin')], default='user')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username già esistente. Scegline un altro.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email già registrata.')


# ==================== ARTISTA FORMS ====================

class ArtistaForm(FlaskForm):
    nome = StringField('Nome Completo', validators=[DataRequired(), Length(max=100)])
    nome_arte = StringField('Nome d\'Arte', validators=[DataRequired(), Length(max=100)])
    biografia = TextAreaField('Biografia')
    genere_musicale = StringField('Genere Musicale', validators=[Length(max=50)])
    foto = FileField('Foto Profilo', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Solo immagini!')])
    data_nascita = DateField('Data di Nascita', validators=[Optional()])
    paese = StringField('Paese', validators=[Length(max=50)])
    sito_web = StringField('Sito Web', validators=[Optional(), URL(), Length(max=200)])
    social_instagram = StringField('Instagram', validators=[Optional(), Length(max=200)])
    social_facebook = StringField('Facebook', validators=[Optional(), Length(max=200)])
    social_twitter = StringField('Twitter', validators=[Optional(), Length(max=200)])
    social_spotify = StringField('Spotify', validators=[Optional(), Length(max=200)])
    attivo = BooleanField('Attivo')


# ==================== DISCO FORMS ====================

class DiscoForm(FlaskForm):
    titolo = StringField('Titolo', validators=[DataRequired(), Length(max=200)])
    descrizione = TextAreaField('Descrizione')
    data_uscita = DateField('Data di Uscita', validators=[Optional()])
    copertina = FileField('Copertina', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Solo immagini!')])
    etichetta = StringField('Etichetta', validators=[Length(max=100)])
    numero_tracce = IntegerField('Numero di Tracce', validators=[Optional()])
    genere = StringField('Genere', validators=[Length(max=50)])
    formato = SelectField('Formato', choices=[
        ('', 'Seleziona formato'),
        ('CD', 'CD'),
        ('Vinile', 'Vinile'),
        ('Digitale', 'Digitale'),
        ('Cassetta', 'Cassetta')
    ])
    codice_catalogo = StringField('Codice Catalogo', validators=[Length(max=50)])
    link_spotify = StringField('Link Spotify', validators=[Optional(), Length(max=200)])
    link_apple_music = StringField('Link Apple Music', validators=[Optional(), Length(max=200)])
    link_youtube = StringField('Link YouTube', validators=[Optional(), Length(max=200)])


# ==================== SINGOLO FORMS ====================

class SingoloForm(FlaskForm):
    titolo = StringField('Titolo', validators=[DataRequired(), Length(max=200)])
    descrizione = TextAreaField('Descrizione')
    data_uscita = DateField('Data di Uscita', validators=[Optional()])
    copertina = FileField('Copertina', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Solo immagini!')])
    durata = StringField('Durata (MM:SS)', validators=[Length(max=20)])
    genere = StringField('Genere', validators=[Length(max=50)])
    etichetta = StringField('Etichetta', validators=[Length(max=100)])
    isrc = StringField('ISRC', validators=[Length(max=50)])
    link_spotify = StringField('Link Spotify', validators=[Optional(), Length(max=200)])
    link_apple_music = StringField('Link Apple Music', validators=[Optional(), Length(max=200)])
    link_youtube = StringField('Link YouTube', validators=[Optional(), Length(max=200)])


# ==================== EVENTO FORMS ====================

class EventoForm(FlaskForm):
    titolo = StringField('Titolo', validators=[DataRequired(), Length(max=200)])
    descrizione = TextAreaField('Descrizione')
    tipo = SelectField('Tipo', choices=[
        ('', 'Seleziona tipo'),
        ('Concerto', 'Concerto'),
        ('Festival', 'Festival'),
        ('Registrazione', 'Registrazione'),
        ('Riunione', 'Riunione'),
        ('Conferenza Stampa', 'Conferenza Stampa'),
        ('Tour', 'Tour'),
        ('Altro', 'Altro')
    ])
    data_inizio = DateTimeField('Data e Ora Inizio', validators=[DataRequired()], format='%Y-%m-%dT%H:%M')
    data_fine = DateTimeField('Data e Ora Fine', validators=[Optional()], format='%Y-%m-%dT%H:%M')
    luogo = StringField('Luogo', validators=[Length(max=200)])
    indirizzo = StringField('Indirizzo', validators=[Length(max=300)])
    citta = StringField('Città', validators=[Length(max=100)])
    paese = StringField('Paese', validators=[Length(max=50)])
    visibilita = SelectField('Visibilità', choices=[('privato', 'Privato'), ('pubblico', 'Pubblico')], default='privato')
    note = TextAreaField('Note')


# ==================== SERVIZIO FORMS ====================

class ServizioForm(FlaskForm):
    nome = StringField('Nome Servizio', validators=[DataRequired(), Length(max=100)])
    descrizione = TextAreaField('Descrizione')
    categoria = SelectField('Categoria', choices=[
        ('', 'Seleziona categoria'),
        ('Produzione', 'Produzione'),
        ('Distribuzione', 'Distribuzione'),
        ('Marketing', 'Marketing'),
        ('Promozione', 'Promozione'),
        ('Management', 'Management'),
        ('Publishing', 'Publishing'),
        ('Tour Management', 'Tour Management'),
        ('Altro', 'Altro')
    ])
    prezzo = DecimalField('Prezzo', validators=[Optional()], places=2)
    valuta = SelectField('Valuta', choices=[('EUR', 'EUR'), ('USD', 'USD'), ('GBP', 'GBP')], default='EUR')
    durata = StringField('Durata', validators=[Length(max=50)])
    attivo = BooleanField('Attivo', default=True)
    icona = SelectField('Icona', choices=[
        ('music', 'Musica'),
        ('microphone', 'Microfono'),
        ('disc', 'Disco'),
        ('radio', 'Radio'),
        ('headphones', 'Cuffie'),
        ('speaker', 'Speaker'),
        ('film', 'Film'),
        ('camera', 'Camera'),
        ('star', 'Stella')
    ])


# ==================== STAFF FORMS ====================

class StaffForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    cognome = StringField('Cognome', validators=[DataRequired(), Length(max=100)])
    ruolo = StringField('Ruolo', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    telefono = StringField('Telefono', validators=[Length(max=20)])
    foto = FileField('Foto', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Solo immagini!')])
    biografia = TextAreaField('Biografia')
    reparto = SelectField('Reparto', choices=[
        ('', 'Seleziona reparto'),
        ('A&R', 'A&R'),
        ('Marketing', 'Marketing'),
        ('Produzione', 'Produzione'),
        ('Distribuzione', 'Distribuzione'),
        ('Amministrazione', 'Amministrazione'),
        ('IT', 'IT'),
        ('Legale', 'Legale'),
        ('HR', 'Risorse Umane')
    ])
    data_assunzione = DateField('Data di Assunzione', validators=[Optional()])
    attivo = BooleanField('Attivo', default=True)


# ==================== DOCUMENTO FORMS ====================

class DocumentoForm(FlaskForm):
    titolo = StringField('Titolo', validators=[DataRequired(), Length(max=200)])
    descrizione = TextAreaField('Descrizione')
    file = FileField('File', validators=[
        DataRequired(),
        FileAllowed(['pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'zip', 'rar'], 'Formato file non supportato!')
    ])
    tipo = SelectField('Tipo', choices=[
        ('', 'Seleziona tipo'),
        ('Contratto', 'Contratto'),
        ('Fattura', 'Fattura'),
        ('Report', 'Report'),
        ('Presentazione', 'Presentazione'),
        ('Accordo', 'Accordo'),
        ('Altro', 'Altro')
    ])
    visibilita = SelectField('Visibilità', choices=[('privato', 'Privato'), ('pubblico', 'Pubblico')], default='privato')


# ==================== NEWS FORMS ====================

class NewsForm(FlaskForm):
    titolo = StringField('Titolo', validators=[DataRequired(), Length(max=200)])
    contenuto = TextAreaField('Contenuto', validators=[DataRequired()])
    sommario = StringField('Sommario', validators=[Length(max=500)])
    immagine = FileField('Immagine', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Solo immagini!')])
    categoria = SelectField('Categoria', choices=[
        ('', 'Seleziona categoria'),
        ('Lancio', 'Lancio'),
        ('Evento', 'Evento'),
        ('Comunicato', 'Comunicato Stampa'),
        ('Intervista', 'Intervista'),
        ('Recensione', 'Recensione'),
        ('Altro', 'Altro')
    ])
    tipo = SelectField('Tipo', choices=[('interna', 'Interna'), ('esterna', 'Esterna')], default='interna')
    pubblicata = BooleanField('Pubblica subito')
    data_pubblicazione = DateTimeField('Data Pubblicazione', validators=[Optional()], format='%Y-%m-%dT%H:%M')


# ==================== RUOLO FORMS ====================

class RuoloForm(FlaskForm):
    nome = StringField('Nome Ruolo', validators=[DataRequired(), Length(max=50)])
    descrizione = StringField('Descrizione', validators=[Length(max=255)])
