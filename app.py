from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from config import Config
from database import init_database, get_db_connection
from models import Utente, Menu, Permesso, Servizio, News
import re
import unicodedata
from datetime import datetime
from functools import wraps
import os
import uuid

app = Flask(__name__)
app.config.from_object(Config)

# Assicura che la cartella uploads esista
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    """Verifica se il file ha un'estensione permessa."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def save_uploaded_file(file):
    """Salva un file uploadato e restituisce il nome del file salvato."""
    if file and file.filename and allowed_file(file.filename):
        # Genera un nome univoco per evitare conflitti
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(filepath)
        return filename
    return None


def delete_uploaded_file(filename):
    """Elimina un file uploadato."""
    if filename:
        filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
        if os.path.exists(filepath):
            os.remove(filepath)


def genera_slug(titolo):
    """Genera uno slug URL-friendly dal titolo."""
    # Normalizza unicode e converti in ASCII
    slug = unicodedata.normalize('NFKD', titolo).encode('ascii', 'ignore').decode('ascii')
    # Converti in minuscolo
    slug = slug.lower()
    # Sostituisci spazi e caratteri non alfanumerici con trattini
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    # Rimuovi trattini iniziali e finali
    slug = slug.strip('-')
    return slug


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Effettua il login per accedere.'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    return Utente.get_by_id(int(user_id))


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Accesso negato. Solo gli amministratori possono accedere.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@app.context_processor
def inject_menu():
    if current_user.is_authenticated:
        menu_items = current_user.get_menu_visibili()
        return dict(menu_items=menu_items)
    return dict(menu_items=[])


# ============ ROUTES AUTENTICAZIONE ============

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        utente = Utente.get_by_username(username)

        if utente and utente.check_password(password):
            if not utente.attivo:
                flash('Account disattivato. Contatta l\'amministratore.', 'danger')
                return render_template('login.html')

            login_user(utente)
            utente.ultimo_accesso = datetime.now()
            utente.save()

            next_page = request.args.get('next')
            flash(f'Benvenuto, {utente.nome}!', 'success')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Username o password non validi.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout effettuato con successo.', 'info')
    return redirect(url_for('login'))


# ============ ROUTES DASHBOARD ============

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


# ============ ROUTES ADMIN UTENTI ============

@app.route('/admin/utenti')
@login_required
@admin_required
def lista_utenti():
    utenti = Utente.get_all()
    return render_template('admin/utenti.html', utenti=utenti)


@app.route('/admin/utenti/nuovo', methods=['GET', 'POST'])
@login_required
@admin_required
def nuovo_utente():
    menu_items_all = Menu.get_all_active()

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        nome = request.form.get('nome')
        cognome = request.form.get('cognome')
        email = request.form.get('email') or None
        is_admin = request.form.get('is_admin') == 'on'

        if Utente.get_by_username(username):
            flash('Username già esistente.', 'danger')
            return render_template('admin/utente_form.html', menu_items_all=menu_items_all)

        if email and Utente.get_by_email(email):
            flash('Email già esistente.', 'danger')
            return render_template('admin/utente_form.html', menu_items_all=menu_items_all)

        utente = Utente(
            username=username,
            nome=nome,
            cognome=cognome,
            email=email,
            is_admin=is_admin
        )
        utente.set_password(password)
        utente.save()

        # Assegna permessi menu - raccogli tutti i menu selezionati
        menu_ids_selezionati = []
        for menu in menu_items_all:
            if request.form.get(f'menu_{menu.id}') == 'on':
                menu_ids_selezionati.append(menu.id)
        Permesso.aggiorna_permessi_utente(utente.id, menu_ids_selezionati)

        flash('Utente creato con successo.', 'success')
        return redirect(url_for('lista_utenti'))

    return render_template('admin/utente_form.html', menu_items_all=menu_items_all, permessi_utente=[])


@app.route('/admin/utenti/<int:id>/modifica', methods=['GET', 'POST'])
@login_required
@admin_required
def modifica_utente(id):
    utente = Utente.get_by_id(id)
    if not utente:
        flash('Utente non trovato.', 'danger')
        return redirect(url_for('lista_utenti'))

    menu_items_all = Menu.get_all_active()
    permessi_utente = Permesso.get_menu_ids_by_utente(utente.id)

    if request.method == 'POST':
        utente.nome = request.form.get('nome')
        utente.cognome = request.form.get('cognome')
        utente.email = request.form.get('email') or None
        utente.is_admin = request.form.get('is_admin') == 'on'
        utente.attivo = request.form.get('attivo') == 'on'

        new_password = request.form.get('password')
        if new_password:
            utente.set_password(new_password)

        utente.save()

        # Aggiorna permessi - raccogli tutti i menu selezionati
        menu_ids_selezionati = []
        for menu in menu_items_all:
            if request.form.get(f'menu_{menu.id}') == 'on':
                menu_ids_selezionati.append(menu.id)
        Permesso.aggiorna_permessi_utente(utente.id, menu_ids_selezionati)

        flash('Utente modificato con successo.', 'success')
        return redirect(url_for('lista_utenti'))

    return render_template('admin/utente_form.html', utente=utente, menu_items_all=menu_items_all, permessi_utente=permessi_utente)


@app.route('/admin/utenti/<int:id>/elimina', methods=['POST'])
@login_required
@admin_required
def elimina_utente(id):
    utente = Utente.get_by_id(id)
    if not utente:
        flash('Utente non trovato.', 'danger')
        return redirect(url_for('lista_utenti'))

    if utente.id == current_user.id:
        flash('Non puoi eliminare te stesso.', 'danger')
        return redirect(url_for('lista_utenti'))

    utente.delete()
    flash('Utente eliminato con successo.', 'success')
    return redirect(url_for('lista_utenti'))


# ============ ROUTES ADMIN MENU ============

@app.route('/admin/menu')
@login_required
@admin_required
def lista_menu():
    menu_items = Menu.get_all()
    return render_template('admin/menu.html', menu_items=menu_items)


@app.route('/admin/menu/nuovo', methods=['GET', 'POST'])
@login_required
@admin_required
def nuovo_menu():
    if request.method == 'POST':
        nome = request.form.get('nome')
        icona = request.form.get('icona') or 'bi-circle'
        url = request.form.get('url')
        ordine = int(request.form.get('ordine') or 0)
        attivo = request.form.get('attivo') == 'on'

        menu = Menu(
            nome=nome,
            icona=icona,
            url=url,
            ordine=ordine,
            attivo=attivo
        )
        menu.save()

        flash('Voce menu creata con successo.', 'success')
        return redirect(url_for('lista_menu'))

    return render_template('admin/menu_form.html')


@app.route('/admin/menu/<int:id>/modifica', methods=['GET', 'POST'])
@login_required
@admin_required
def modifica_menu(id):
    menu = Menu.get_by_id(id)
    if not menu:
        flash('Voce menu non trovata.', 'danger')
        return redirect(url_for('lista_menu'))

    if request.method == 'POST':
        menu.nome = request.form.get('nome')
        menu.icona = request.form.get('icona') or 'bi-circle'
        menu.url = request.form.get('url')
        menu.ordine = int(request.form.get('ordine') or 0)
        menu.attivo = request.form.get('attivo') == 'on'

        menu.save()

        flash('Voce menu modificata con successo.', 'success')
        return redirect(url_for('lista_menu'))

    return render_template('admin/menu_form.html', menu=menu)


@app.route('/admin/menu/<int:id>/elimina', methods=['POST'])
@login_required
@admin_required
def elimina_menu(id):
    menu = Menu.get_by_id(id)
    if not menu:
        flash('Voce menu non trovata.', 'danger')
        return redirect(url_for('lista_menu'))

    menu.delete()
    flash('Voce menu eliminata con successo.', 'success')
    return redirect(url_for('lista_menu'))


# ============ ROUTES ADMIN SERVIZI ============

@app.route('/admin/servizi')
@login_required
@admin_required
def lista_servizi():
    servizi = Servizio.get_all()
    return render_template('admin/servizi.html', servizi=servizi)


@app.route('/admin/servizi/nuovo', methods=['GET', 'POST'])
@login_required
@admin_required
def nuovo_servizio():
    if request.method == 'POST':
        nome = request.form.get('nome')
        descrizione = request.form.get('descrizione') or None
        descrizione_breve = request.form.get('descrizione_breve') or None
        icona = request.form.get('icona') or 'bi-gear'
        prezzo = request.form.get('prezzo') or None
        if prezzo:
            prezzo = float(prezzo)
        durata = request.form.get('durata') or None
        ordine = int(request.form.get('ordine') or 0)
        attivo = request.form.get('attivo') == 'on'
        in_evidenza = request.form.get('in_evidenza') == 'on'

        # Gestione upload immagine
        foto = None
        if 'foto' in request.files:
            file = request.files['foto']
            if file and file.filename:
                foto = save_uploaded_file(file)
                if not foto and file.filename:
                    flash('Formato immagine non valido. Usa: png, jpg, jpeg, gif, webp', 'warning')

        servizio = Servizio(
            nome=nome,
            descrizione=descrizione,
            descrizione_breve=descrizione_breve,
            foto=foto,
            icona=icona,
            prezzo=prezzo,
            durata=durata,
            ordine=ordine,
            attivo=attivo,
            in_evidenza=in_evidenza
        )
        servizio.save()

        flash('Servizio creato con successo.', 'success')
        return redirect(url_for('lista_servizi'))

    return render_template('admin/servizio_form.html')


@app.route('/admin/servizi/<int:id>/modifica', methods=['GET', 'POST'])
@login_required
@admin_required
def modifica_servizio(id):
    servizio = Servizio.get_by_id(id)
    if not servizio:
        flash('Servizio non trovato.', 'danger')
        return redirect(url_for('lista_servizi'))

    if request.method == 'POST':
        servizio.nome = request.form.get('nome')
        servizio.descrizione = request.form.get('descrizione') or None
        servizio.descrizione_breve = request.form.get('descrizione_breve') or None
        servizio.icona = request.form.get('icona') or 'bi-gear'
        prezzo = request.form.get('prezzo') or None
        if prezzo:
            servizio.prezzo = float(prezzo)
        else:
            servizio.prezzo = None
        servizio.durata = request.form.get('durata') or None
        servizio.ordine = int(request.form.get('ordine') or 0)
        servizio.attivo = request.form.get('attivo') == 'on'
        servizio.in_evidenza = request.form.get('in_evidenza') == 'on'

        # Gestione upload immagine
        if 'foto' in request.files:
            file = request.files['foto']
            if file and file.filename:
                new_foto = save_uploaded_file(file)
                if new_foto:
                    # Elimina la vecchia immagine se esiste
                    delete_uploaded_file(servizio.foto)
                    servizio.foto = new_foto
                else:
                    flash('Formato immagine non valido. Usa: png, jpg, jpeg, gif, webp', 'warning')

        # Rimuovi immagine se richiesto
        if request.form.get('rimuovi_foto') == 'on':
            delete_uploaded_file(servizio.foto)
            servizio.foto = None

        servizio.save()

        flash('Servizio modificato con successo.', 'success')
        return redirect(url_for('lista_servizi'))

    return render_template('admin/servizio_form.html', servizio=servizio)


@app.route('/admin/servizi/<int:id>/elimina', methods=['POST'])
@login_required
@admin_required
def elimina_servizio(id):
    servizio = Servizio.get_by_id(id)
    if not servizio:
        flash('Servizio non trovato.', 'danger')
        return redirect(url_for('lista_servizi'))

    # Elimina l'immagine associata
    delete_uploaded_file(servizio.foto)

    servizio.delete()
    flash('Servizio eliminato con successo.', 'success')
    return redirect(url_for('lista_servizi'))


# ============ ROUTES ADMIN NEWS ============

@app.route('/admin/news')
@login_required
@admin_required
def lista_news():
    news_list = News.get_all()
    return render_template('admin/news.html', news_list=news_list)


@app.route('/admin/news/nuovo', methods=['GET', 'POST'])
@login_required
@admin_required
def nuova_news():
    if request.method == 'POST':
        titolo = request.form.get('titolo')
        slug = request.form.get('slug') or genera_slug(titolo)
        contenuto = request.form.get('contenuto') or None
        estratto = request.form.get('estratto') or None
        categoria = request.form.get('categoria') or None
        tags = request.form.get('tags') or None
        pubblicato = request.form.get('pubblicato') == 'on'
        in_evidenza = request.form.get('in_evidenza') == 'on'

        # Data pubblicazione
        data_pubblicazione = None
        data_pub_str = request.form.get('data_pubblicazione')
        if data_pub_str:
            try:
                data_pubblicazione = datetime.strptime(data_pub_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass

        # Verifica slug univoco
        existing = News.get_by_slug(slug)
        if existing:
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"

        # Gestione upload immagine
        immagine = None
        if 'immagine' in request.files:
            file = request.files['immagine']
            if file and file.filename:
                immagine = save_uploaded_file(file)
                if not immagine and file.filename:
                    flash('Formato immagine non valido. Usa: png, jpg, jpeg, gif, webp', 'warning')

        news = News(
            titolo=titolo,
            slug=slug,
            contenuto=contenuto,
            estratto=estratto,
            immagine=immagine,
            autore_id=current_user.id,
            categoria=categoria,
            tags=tags,
            pubblicato=pubblicato,
            in_evidenza=in_evidenza,
            data_pubblicazione=data_pubblicazione
        )
        news.save()

        flash('News creata con successo.', 'success')
        return redirect(url_for('lista_news'))

    return render_template('admin/news_form.html')


@app.route('/admin/news/<int:id>/modifica', methods=['GET', 'POST'])
@login_required
@admin_required
def modifica_news(id):
    news = News.get_by_id(id)
    if not news:
        flash('News non trovata.', 'danger')
        return redirect(url_for('lista_news'))

    if request.method == 'POST':
        news.titolo = request.form.get('titolo')
        new_slug = request.form.get('slug') or genera_slug(news.titolo)

        # Verifica slug univoco (escludi la news corrente)
        existing = News.get_by_slug(new_slug)
        if existing and existing.id != news.id:
            new_slug = f"{new_slug}-{uuid.uuid4().hex[:6]}"
        news.slug = new_slug

        news.contenuto = request.form.get('contenuto') or None
        news.estratto = request.form.get('estratto') or None
        news.categoria = request.form.get('categoria') or None
        news.tags = request.form.get('tags') or None
        news.pubblicato = request.form.get('pubblicato') == 'on'
        news.in_evidenza = request.form.get('in_evidenza') == 'on'

        # Data pubblicazione
        data_pub_str = request.form.get('data_pubblicazione')
        if data_pub_str:
            try:
                news.data_pubblicazione = datetime.strptime(data_pub_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
        else:
            news.data_pubblicazione = None

        # Gestione upload immagine
        if 'immagine' in request.files:
            file = request.files['immagine']
            if file and file.filename:
                new_immagine = save_uploaded_file(file)
                if new_immagine:
                    delete_uploaded_file(news.immagine)
                    news.immagine = new_immagine
                else:
                    flash('Formato immagine non valido. Usa: png, jpg, jpeg, gif, webp', 'warning')

        # Rimuovi immagine se richiesto
        if request.form.get('rimuovi_immagine') == 'on':
            delete_uploaded_file(news.immagine)
            news.immagine = None

        news.save()

        flash('News modificata con successo.', 'success')
        return redirect(url_for('lista_news'))

    return render_template('admin/news_form.html', news=news)


@app.route('/admin/news/<int:id>/elimina', methods=['POST'])
@login_required
@admin_required
def elimina_news(id):
    news = News.get_by_id(id)
    if not news:
        flash('News non trovata.', 'danger')
        return redirect(url_for('lista_news'))

    # Elimina l'immagine associata
    delete_uploaded_file(news.immagine)

    news.delete()
    flash('News eliminata con successo.', 'success')
    return redirect(url_for('lista_news'))


# ============ INIZIALIZZAZIONE DATABASE ============

def init_db():
    """Inizializza il database con tabelle e dati di default."""
    init_database()

    # Crea admin se non esiste
    if not Utente.get_by_username('admin'):
        admin = Utente(
            username='admin',
            nome='Amministratore',
            cognome='Sistema',
            email='admin@gestionale.local',
            is_admin=True
        )
        admin.set_password('admin123')
        admin.save()

        # Crea voci menu di default
        menu_dashboard = Menu(nome='Dashboard', icona='bi-speedometer2', url='/dashboard', ordine=0)
        menu_dashboard.save()

        menu_utenti = Menu(nome='Utenti', icona='bi-people', url='/admin/utenti', ordine=1)
        menu_utenti.save()

        menu_gestione_menu = Menu(nome='Gestione Menu', icona='bi-list-ul', url='/admin/menu', ordine=2)
        menu_gestione_menu.save()

        menu_servizi = Menu(nome='Servizi', icona='bi-briefcase', url='/admin/servizi', ordine=3)
        menu_servizi.save()

        menu_news = Menu(nome='News', icona='bi-newspaper', url='/admin/news', ordine=4)
        menu_news.save()

        print('Database inizializzato con utente admin (password: admin123)')


if __name__ == '__main__':
    init_db()
    app.run(debug=True,host="0.0.0.0")
