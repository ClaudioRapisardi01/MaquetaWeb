from flask import Flask, render_template, redirect, url_for, flash, request, send_file, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import nas_storage
from config import Config
from database import init_database, get_db_connection
from models import Utente, Menu, Permesso, CategoriaServizio, Servizio, News, Artista, MembroBand, Disco, Brano, Evento
import re
import unicodedata
from datetime import datetime
from functools import wraps
import os
import uuid

app = Flask(__name__)
app.config.from_object(Config)

# Rimuove il limite globale di upload (necessario per il file manager NAS senza limiti).
# La validazione delle dimensioni per gli upload normali (immagini) avviene a livello applicativo.
app.config['MAX_CONTENT_LENGTH'] = None

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


def artista_required(f):
    """Richiede che l'utente sia collegato a un artista (o sia admin)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if not current_user.is_admin and not current_user.artista_id:
            flash('Accesso negato. Questa sezione e riservata agli artisti.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def _get_file_manager_username():
    """Restituisce lo username da usare per le operazioni file manager.
    Gli admin possono selezionare un altro utente o lo spazio condiviso."""
    if current_user.is_admin:
        shared = request.form.get('shared') or request.args.get('shared')
        if shared == '1':
            return '__condivisi__'
        user_id = request.form.get('target_user_id') or request.args.get('user_id')
        if user_id:
            target_user = Utente.get_by_id(int(user_id))
            if target_user:
                return target_user.username
    return current_user.username


def _get_hidden_files(username):
    """Restituisce un set di percorsi nascosti per un dato username."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT percorso FROM file_nascosti WHERE username = %s', (username,))
    result = {row['percorso'] for row in cursor.fetchall()}
    cursor.close()
    conn.close()
    return result


def _build_file_path(subpath, filename):
    """Costruisce il percorso relativo di un file."""
    if subpath:
        return f"{subpath}/{filename}"
    return filename


def _get_deleted_files(username):
    """Restituisce un set di percorsi eliminati logicamente per un dato username."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT percorso FROM file_cestino WHERE username = %s', (username,))
    result = {row['percorso'] for row in cursor.fetchall()}
    cursor.close()
    conn.close()
    return result


def _purge_expired_files():
    """Elimina fisicamente dal NAS i file nel cestino da piu di 30 giorni."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, username, percorso FROM file_cestino WHERE data_eliminazione < NOW() - INTERVAL 30 DAY'
    )
    expired = cursor.fetchall()
    for item in expired:
        # Separa subpath e filename dal percorso
        percorso = item['percorso']
        if '/' in percorso:
            parts = percorso.rsplit('/', 1)
            subpath, filename = parts[0], parts[1]
        else:
            subpath, filename = '', percorso
        try:
            nas_storage.delete_file(item['username'], subpath, filename)
        except Exception:
            pass
        cursor.execute('DELETE FROM file_cestino WHERE id = %s', (item['id'],))
    conn.commit()
    cursor.close()
    conn.close()


# Mapping per route che non corrispondono direttamente a un URL di menu
# es. /admin/membri/* fa parte della sezione Artisti
ROUTE_MENU_MAPPING = {
    '/admin/membri': '/admin/artisti',
}


def permesso_menu_required(f):
    """Permette l'accesso se l'utente e admin o ha il permesso menu corrispondente."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        # Admin ha sempre accesso
        if current_user.is_admin:
            return f(*args, **kwargs)
        # Per utenti normali, verifica se hanno un permesso menu che copre questo path
        menu_visibili = current_user.get_menu_visibili()
        menu_urls = [menu.url for menu in menu_visibili]
        path = request.path
        # Verifica corrispondenza diretta
        for url in menu_urls:
            if path == url or path.startswith(url + '/'):
                return f(*args, **kwargs)
        # Verifica route mappate (es. /admin/membri -> /admin/artisti)
        for route_prefix, menu_url in ROUTE_MENU_MAPPING.items():
            if path.startswith(route_prefix) and menu_url in menu_urls:
                return f(*args, **kwargs)
        flash('Accesso negato. Non hai i permessi per questa sezione.', 'danger')
        return redirect(url_for('dashboard'))
    return decorated_function


@app.context_processor
def inject_menu():
    if current_user.is_authenticated:
        menu_items = current_user.get_menu_visibili()
        is_artista = current_user.artista_id is not None
        return dict(menu_items=menu_items, is_artista=is_artista)
    return dict(menu_items=[], is_artista=False)


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


@app.route('/cambia-password', methods=['GET', 'POST'])
@login_required
def reset_password_self():
    if request.method == 'POST':
        password_attuale = request.form.get('password_attuale')
        nuova_password = request.form.get('nuova_password')
        conferma_password = request.form.get('conferma_password')

        if not current_user.check_password(password_attuale):
            flash('La password attuale non è corretta.', 'danger')
            return render_template('cambia_password.html')

        if nuova_password != conferma_password:
            flash('Le nuove password non coincidono.', 'danger')
            return render_template('cambia_password.html')

        if len(nuova_password) < 6:
            flash('La nuova password deve essere di almeno 6 caratteri.', 'danger')
            return render_template('cambia_password.html')

        current_user.set_password(nuova_password)
        current_user.save()
        flash('Password cambiata con successo!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('cambia_password.html')


@app.route('/profilo', methods=['GET', 'POST'])
@login_required
def profilo():
    if request.method == 'POST':
        nome = request.form.get('nome')
        cognome = request.form.get('cognome')
        email = request.form.get('email') or None

        if not nome or not cognome:
            flash('Nome e cognome sono obbligatori.', 'danger')
            return render_template('profilo.html')

        # Verifica che l'email non sia gia usata da un altro utente
        if email:
            existing = Utente.get_by_email(email)
            if existing and existing.id != current_user.id:
                flash('Questa email e gia utilizzata da un altro utente.', 'danger')
                return render_template('profilo.html')

        current_user.nome = nome
        current_user.cognome = cognome
        current_user.email = email
        current_user.save()

        flash('Profilo aggiornato con successo.', 'success')
        return redirect(url_for('profilo'))

    return render_template('profilo.html')


# ============ ROUTES FILE MANAGER ============

@app.route('/file-manager')
@login_required
def file_manager():
    subpath = request.args.get('path', '')
    shared = request.args.get('shared') == '1'

    # Admin puo navigare file di altri utenti
    target_username = current_user.username
    selected_user_id = None
    all_users = []

    if shared:
        if not current_user.is_admin:
            flash('Accesso non autorizzato.', 'danger')
            return redirect(url_for('file_manager'))
        target_username = '__condivisi__'
        try:
            nas_storage.ensure_shared_folder()
        except Exception:
            pass
    elif current_user.is_admin:
        # Mostra solo gli utenti artisti nel selettore (non gli altri admin)
        all_users = [u for u in Utente.get_all() if u.artista_id]
        selected_user_id = request.args.get('user_id')
        if selected_user_id:
            target_user = Utente.get_by_id(int(selected_user_id))
            if target_user and target_user.artista_id:
                target_username = target_user.username
            else:
                selected_user_id = None

    try:
        files = nas_storage.list_files(target_username, subpath)
    except Exception as e:
        flash(f'Errore di connessione al NAS: {str(e)}', 'danger')
        files = []

    # Purge file scaduti dal cestino (oltre 30 giorni)
    try:
        _purge_expired_files()
    except Exception:
        pass

    # Filtraggio file nel cestino (eliminati logicamente)
    deleted = _get_deleted_files(target_username)
    if deleted:
        files = [f for f in files if _build_file_path(subpath, f['name']) not in deleted]

    # Filtraggio file nascosti
    if not current_user.is_admin and not shared:
        # Artista: nascondi i file marcati come nascosti
        hidden = _get_hidden_files(target_username)
        if hidden:
            files = [f for f in files if _build_file_path(subpath, f['name']) not in hidden]
    elif current_user.is_admin and selected_user_id and not shared:
        # Admin che naviga file di un artista: mostra tutto ma segna i nascosti
        hidden = _get_hidden_files(target_username)
        for f in files:
            f['nascosto'] = _build_file_path(subpath, f['name']) in hidden
    else:
        for f in files:
            f['nascosto'] = False

    # Costruisci breadcrumb
    breadcrumb = []
    if subpath:
        parts = nas_storage._safe_subpath(subpath).split('/')
        for i, part in enumerate(parts):
            breadcrumb.append({
                'name': part,
                'path': '/'.join(parts[:i+1])
            })

    return render_template('file_manager.html', files=files, subpath=subpath,
                           breadcrumb=breadcrumb, get_file_icon=nas_storage.get_file_icon,
                           all_users=all_users, selected_user_id=selected_user_id,
                           shared=shared)


def _file_manager_redirect(subpath, user_id=None, shared=False):
    """Helper per redirect consistente nelle route file manager."""
    params = {'path': subpath} if subpath else {}
    if shared:
        params['shared'] = '1'
    elif user_id:
        params['user_id'] = user_id
    return redirect(url_for('file_manager', **params))


@app.route('/file-manager/upload', methods=['POST'])
@login_required
def file_manager_upload():
    subpath = request.form.get('subpath', '')
    target_username = _get_file_manager_username()
    user_id = request.form.get('target_user_id', '')
    shared = request.form.get('shared') == '1'

    if 'files' not in request.files:
        flash('Nessun file selezionato.', 'warning')
        return _file_manager_redirect(subpath, user_id, shared)

    files = request.files.getlist('files')
    uploaded = 0
    errors = 0

    for file in files:
        if file and file.filename:
            try:
                success = nas_storage.upload_file(
                    target_username, subpath, file.stream, file.filename
                )
                if success:
                    uploaded += 1
                else:
                    errors += 1
            except Exception:
                errors += 1

    if uploaded > 0:
        flash(f'{uploaded} file caricato/i con successo.', 'success')
    if errors > 0:
        flash(f'{errors} file non caricato/i per errori.', 'danger')

    return _file_manager_redirect(subpath, user_id, shared)


@app.route('/file-manager/download')
@login_required
def file_manager_download():
    subpath = request.args.get('path', '')
    filename = request.args.get('file', '')
    target_username = current_user.username

    if current_user.is_admin:
        if request.args.get('shared') == '1':
            target_username = '__condivisi__'
        else:
            user_id = request.args.get('user_id')
            if user_id:
                target_user = Utente.get_by_id(int(user_id))
                if target_user:
                    target_username = target_user.username

    if not filename:
        return 'File non specificato.', 400

    buffer = nas_storage.download_file(target_username, subpath, filename)
    if buffer is None:
        return 'Errore durante il download del file.', 500

    return send_file(buffer, download_name=filename, as_attachment=True, mimetype='application/octet-stream')


@app.route('/file-manager/delete', methods=['POST'])
@login_required
def file_manager_delete():
    subpath = request.form.get('subpath', '')
    filename = request.form.get('filename', '')
    target_username = _get_file_manager_username()
    user_id = request.form.get('target_user_id', '')
    shared = request.form.get('shared') == '1'

    if not filename:
        flash('File non specificato.', 'danger')
        return _file_manager_redirect(subpath, user_id, shared)

    # Eliminazione logica: il file resta sul NAS ma viene nascosto
    percorso = _build_file_path(subpath, filename)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT IGNORE INTO file_cestino (username, percorso, eliminato_da) VALUES (%s, %s, %s)',
            (target_username, percorso, current_user.id)
        )
        conn.commit()
        flash(f'File "{filename}" spostato nel cestino. Verra eliminato definitivamente tra 30 giorni.', 'success')
    except Exception:
        flash(f'Errore durante l\'eliminazione del file "{filename}".', 'danger')
    finally:
        cursor.close()
        conn.close()

    return _file_manager_redirect(subpath, user_id, shared)


@app.route('/file-manager/rinomina', methods=['POST'])
@login_required
def file_manager_rinomina():
    subpath = request.form.get('subpath', '')
    old_name = request.form.get('old_name', '')
    new_name = request.form.get('new_name', '').strip()
    target_username = _get_file_manager_username()
    user_id = request.form.get('target_user_id', '')
    shared = request.form.get('shared') == '1'

    if not old_name or not new_name:
        flash('Nome non valido.', 'danger')
        return _file_manager_redirect(subpath, user_id, shared)

    success = nas_storage.rename_item(target_username, subpath, old_name, new_name)
    if success:
        flash(f'"{old_name}" rinominato in "{new_name}" con successo.', 'success')
    else:
        flash(f'Errore durante la rinomina. Verifica che il nuovo nome non sia già in uso.', 'danger')

    return _file_manager_redirect(subpath, user_id, shared)


@app.route('/file-manager/nuova-cartella', methods=['POST'])
@login_required
def file_manager_nuova_cartella():
    subpath = request.form.get('subpath', '')
    folder_name = request.form.get('folder_name', '').strip()
    target_username = _get_file_manager_username()
    user_id = request.form.get('target_user_id', '')
    shared = request.form.get('shared') == '1'

    if not folder_name:
        flash('Nome cartella non valido.', 'danger')
        return _file_manager_redirect(subpath, user_id, shared)

    success = nas_storage.create_folder(target_username, subpath, folder_name)
    if success:
        flash(f'Cartella "{folder_name}" creata con successo.', 'success')
    else:
        flash(f'Errore durante la creazione della cartella.', 'danger')

    return _file_manager_redirect(subpath, user_id, shared)


@app.route('/file-manager/elimina-cartella', methods=['POST'])
@login_required
def file_manager_elimina_cartella():
    subpath = request.form.get('subpath', '')
    folder_name = request.form.get('folder_name', '')
    target_username = _get_file_manager_username()
    user_id = request.form.get('target_user_id', '')
    shared = request.form.get('shared') == '1'

    if not folder_name:
        flash('Cartella non specificata.', 'danger')
        return _file_manager_redirect(subpath, user_id, shared)

    # Eliminazione logica della cartella
    percorso = _build_file_path(subpath, folder_name)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT IGNORE INTO file_cestino (username, percorso, eliminato_da) VALUES (%s, %s, %s)',
            (target_username, percorso, current_user.id)
        )
        conn.commit()
        flash(f'Cartella "{folder_name}" spostata nel cestino. Verra eliminata definitivamente tra 30 giorni.', 'success')
    except Exception:
        flash('Errore durante l\'eliminazione della cartella.', 'danger')
    finally:
        cursor.close()
        conn.close()

    return _file_manager_redirect(subpath, user_id, shared)


@app.route('/file-manager/nascondi', methods=['POST'])
@login_required
@admin_required
def file_manager_nascondi():
    subpath = request.form.get('subpath', '')
    filename = request.form.get('filename', '')
    user_id = request.form.get('target_user_id', '')
    target_username = _get_file_manager_username()

    if not filename or not user_id:
        flash('Operazione non valida.', 'danger')
        return _file_manager_redirect(subpath, user_id, False)

    percorso = _build_file_path(subpath, filename)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT IGNORE INTO file_nascosti (username, percorso, nascosto_da) VALUES (%s, %s, %s)',
            (target_username, percorso, current_user.id)
        )
        conn.commit()
        flash(f'"{filename}" nascosto all\'artista.', 'success')
    except Exception:
        flash('Errore durante l\'operazione.', 'danger')
    finally:
        cursor.close()
        conn.close()

    return _file_manager_redirect(subpath, user_id, False)


@app.route('/file-manager/mostra', methods=['POST'])
@login_required
@admin_required
def file_manager_mostra():
    subpath = request.form.get('subpath', '')
    filename = request.form.get('filename', '')
    user_id = request.form.get('target_user_id', '')
    target_username = _get_file_manager_username()

    if not filename or not user_id:
        flash('Operazione non valida.', 'danger')
        return _file_manager_redirect(subpath, user_id, False)

    percorso = _build_file_path(subpath, filename)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'DELETE FROM file_nascosti WHERE username = %s AND percorso = %s',
            (target_username, percorso)
        )
        conn.commit()
        flash(f'"{filename}" ora visibile all\'artista.', 'success')
    except Exception:
        flash('Errore durante l\'operazione.', 'danger')
    finally:
        cursor.close()
        conn.close()

    return _file_manager_redirect(subpath, user_id, False)


# ============ ROUTES DASHBOARD ============

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.artista_id and not current_user.is_admin:
        return redirect(url_for('artista_dashboard'))
    return render_template('dashboard.html')


# ============ API IMMAGINI ============

@app.route('/api/immagini')
@login_required
@admin_required
def api_immagini():
    """Restituisce la lista delle immagini caricate."""
    import json
    immagini = []
    upload_folder = Config.UPLOAD_FOLDER

    if os.path.exists(upload_folder):
        for filename in os.listdir(upload_folder):
            if allowed_file(filename):
                filepath = os.path.join(upload_folder, filename)
                stat = os.stat(filepath)
                immagini.append({
                    'filename': filename,
                    'url': url_for('static', filename='uploads/' + filename),
                    'size': stat.st_size,
                    'modified': stat.st_mtime
                })

    # Ordina per data di modifica (piu recenti prima)
    immagini.sort(key=lambda x: x['modified'], reverse=True)

    return json.dumps(immagini), 200, {'Content-Type': 'application/json'}


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
@permesso_menu_required
def lista_servizi():
    categoria_filtro = request.args.get('categoria', type=int)
    if categoria_filtro:
        servizi = Servizio.get_by_categoria(categoria_filtro)
    else:
        servizi = Servizio.get_all()
    categorie = CategoriaServizio.get_all()
    # Mappa id -> nome categoria per visualizzazione rapida
    categorie_map = {c.id: c.nome for c in categorie}
    return render_template('admin/servizi.html', servizi=servizi, categorie=categorie,
                           categorie_map=categorie_map, categoria_filtro=categoria_filtro)


@app.route('/admin/servizi/nuovo', methods=['GET', 'POST'])
@login_required
@permesso_menu_required
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
        categoria_id = request.form.get('categoria_id') or None
        if categoria_id:
            categoria_id = int(categoria_id)

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
            in_evidenza=in_evidenza,
            categoria_id=categoria_id
        )
        servizio.save()

        flash('Servizio creato con successo.', 'success')
        return redirect(url_for('lista_servizi'))

    categorie = CategoriaServizio.get_all_active()
    return render_template('admin/servizio_form.html', categorie=categorie)


@app.route('/admin/servizi/<int:id>/modifica', methods=['GET', 'POST'])
@login_required
@permesso_menu_required
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
        categoria_id = request.form.get('categoria_id') or None
        if categoria_id:
            servizio.categoria_id = int(categoria_id)
        else:
            servizio.categoria_id = None

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

    categorie = CategoriaServizio.get_all_active()
    return render_template('admin/servizio_form.html', servizio=servizio, categorie=categorie)


@app.route('/admin/servizi/<int:id>/elimina', methods=['POST'])
@login_required
@permesso_menu_required
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


# ============ ROUTES ADMIN CATEGORIE SERVIZI ============

@app.route('/admin/categorie-servizi')
@login_required
@permesso_menu_required
def lista_categorie_servizi():
    categorie = CategoriaServizio.get_all()
    return render_template('admin/categorie_servizi.html', categorie=categorie)


@app.route('/admin/categorie-servizi/nuova', methods=['GET', 'POST'])
@login_required
@permesso_menu_required
def nuova_categoria_servizio():
    if request.method == 'POST':
        nome = request.form.get('nome')
        descrizione = request.form.get('descrizione') or None
        icona = request.form.get('icona') or 'bi-folder'
        ordine = int(request.form.get('ordine') or 0)
        attivo = request.form.get('attivo') == 'on'

        categoria = CategoriaServizio(
            nome=nome,
            descrizione=descrizione,
            icona=icona,
            ordine=ordine,
            attivo=attivo
        )
        categoria.save()

        flash('Categoria creata con successo.', 'success')
        return redirect(url_for('lista_categorie_servizi'))

    return render_template('admin/categoria_servizio_form.html')


@app.route('/admin/categorie-servizi/<int:id>/modifica', methods=['GET', 'POST'])
@login_required
@permesso_menu_required
def modifica_categoria_servizio(id):
    categoria = CategoriaServizio.get_by_id(id)
    if not categoria:
        flash('Categoria non trovata.', 'danger')
        return redirect(url_for('lista_categorie_servizi'))

    if request.method == 'POST':
        categoria.nome = request.form.get('nome')
        categoria.descrizione = request.form.get('descrizione') or None
        categoria.icona = request.form.get('icona') or 'bi-folder'
        categoria.ordine = int(request.form.get('ordine') or 0)
        categoria.attivo = request.form.get('attivo') == 'on'

        categoria.save()

        flash('Categoria modificata con successo.', 'success')
        return redirect(url_for('lista_categorie_servizi'))

    return render_template('admin/categoria_servizio_form.html', categoria=categoria)


@app.route('/admin/categorie-servizi/<int:id>/elimina', methods=['POST'])
@login_required
@permesso_menu_required
def elimina_categoria_servizio(id):
    categoria = CategoriaServizio.get_by_id(id)
    if not categoria:
        flash('Categoria non trovata.', 'danger')
        return redirect(url_for('lista_categorie_servizi'))

    categoria.delete()
    flash('Categoria eliminata con successo. I servizi associati non hanno piu una categoria.', 'success')
    return redirect(url_for('lista_categorie_servizi'))


# ============ ROUTES ADMIN NEWS ============

@app.route('/admin/news')
@login_required
@permesso_menu_required
def lista_news():
    news_list = News.get_all()
    return render_template('admin/news.html', news_list=news_list)


@app.route('/admin/news/nuovo', methods=['GET', 'POST'])
@login_required
@permesso_menu_required
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

        # Gestione upload immagine o selezione dalla galleria
        immagine = None
        immagine_esistente = request.form.get('immagine_esistente')

        if immagine_esistente:
            # Usa immagine esistente dalla galleria
            immagine = immagine_esistente
        elif 'immagine' in request.files:
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
@permesso_menu_required
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

        # Gestione upload immagine o selezione dalla galleria
        immagine_esistente = request.form.get('immagine_esistente')

        if immagine_esistente:
            # Usa immagine esistente dalla galleria (non elimina la vecchia perche potrebbe essere usata altrove)
            news.immagine = immagine_esistente
        elif 'immagine' in request.files:
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
@permesso_menu_required
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


# ============ ROUTES ADMIN ARTISTI ============

@app.route('/admin/artisti')
@login_required
@permesso_menu_required
def lista_artisti():
    artisti = Artista.get_all()
    return render_template('admin/artisti.html', artisti=artisti)


@app.route('/admin/artisti/nuovo', methods=['GET', 'POST'])
@login_required
@permesso_menu_required
def nuovo_artista():
    if request.method == 'POST':
        nome = request.form.get('nome')
        nome_arte = request.form.get('nome_arte') or None
        slug = request.form.get('slug') or genera_slug(nome_arte or nome)
        bio = request.form.get('bio') or None
        is_band = request.form.get('is_band') == 'on'

        # Social links
        instagram = request.form.get('instagram') or None
        facebook = request.form.get('facebook') or None
        twitter = request.form.get('twitter') or None
        spotify = request.form.get('spotify') or None
        youtube = request.form.get('youtube') or None
        apple_music = request.form.get('apple_music') or None
        website = request.form.get('website') or None

        # Metadati
        genere = request.form.get('genere') or None
        anno_fondazione = request.form.get('anno_fondazione') or None
        if anno_fondazione:
            anno_fondazione = int(anno_fondazione)
        paese = request.form.get('paese') or None
        citta = request.form.get('citta') or None

        # Stato
        ordine = int(request.form.get('ordine') or 0)
        attivo = request.form.get('attivo') == 'on'
        in_evidenza = request.form.get('in_evidenza') == 'on'

        # Verifica slug univoco
        existing = Artista.get_by_slug(slug)
        if existing:
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"

        # Gestione upload foto
        foto = None
        if 'foto' in request.files:
            file = request.files['foto']
            if file and file.filename:
                foto = save_uploaded_file(file)
                if not foto and file.filename:
                    flash('Formato immagine non valido. Usa: png, jpg, jpeg, gif, webp', 'warning')

        # Gestione upload foto copertina
        foto_copertina = None
        if 'foto_copertina' in request.files:
            file = request.files['foto_copertina']
            if file and file.filename:
                foto_copertina = save_uploaded_file(file)
                if not foto_copertina and file.filename:
                    flash('Formato immagine copertina non valido.', 'warning')

        email_artista = request.form.get('email_artista') or None

        artista = Artista(
            nome=nome,
            nome_arte=nome_arte,
            slug=slug,
            bio=bio,
            foto=foto,
            foto_copertina=foto_copertina,
            is_band=is_band,
            instagram=instagram,
            facebook=facebook,
            twitter=twitter,
            spotify=spotify,
            youtube=youtube,
            apple_music=apple_music,
            website=website,
            email=email_artista,
            genere=genere,
            anno_fondazione=anno_fondazione,
            paese=paese,
            citta=citta,
            attivo=attivo,
            in_evidenza=in_evidenza,
            ordine=ordine
        )
        artista.save()

        # Creazione automatica account artista
        if email_artista:
            existing_user = Utente.get_by_username(email_artista)
            if existing_user:
                flash(f'Attenzione: esiste gia un utente con username "{email_artista}". Account artista non creato.', 'warning')
            else:
                import secrets
                import string
                alphabet = string.ascii_letters + string.digits
                password_generata = ''.join(secrets.choice(alphabet) for _ in range(12))

                nuovo_utente = Utente(
                    username=email_artista,
                    nome=artista.nome_arte or artista.nome,
                    cognome='',
                    email=email_artista,
                    is_admin=False,
                    attivo=True,
                    artista_id=artista.id
                )
                nuovo_utente.set_password(password_generata)
                nuovo_utente.save()

                try:
                    nas_storage.ensure_user_folder(email_artista)
                except Exception:
                    pass

                session['credenziali_artista'] = {'username': email_artista, 'password': password_generata}
                flash('Artista e account creati con successo.', 'success')
                return redirect(url_for('credenziali_artista', id=artista.id))

        flash('Artista creato con successo.', 'success')
        return redirect(url_for('modifica_artista', id=artista.id))

    return render_template('admin/artista_form.html')


@app.route('/admin/artisti/<int:id>/modifica', methods=['GET', 'POST'])
@login_required
@permesso_menu_required
def modifica_artista(id):
    artista = Artista.get_by_id(id)
    if not artista:
        flash('Artista non trovato.', 'danger')
        return redirect(url_for('lista_artisti'))

    # Carica dati correlati
    membri = artista.get_membri() if artista.is_band else []
    dischi = artista.get_dischi()
    eventi = artista.get_eventi()

    if request.method == 'POST':
        artista.nome = request.form.get('nome')
        artista.nome_arte = request.form.get('nome_arte') or None

        new_slug = request.form.get('slug') or genera_slug(artista.nome_arte or artista.nome)
        existing = Artista.get_by_slug(new_slug)
        if existing and existing.id != artista.id:
            new_slug = f"{new_slug}-{uuid.uuid4().hex[:6]}"
        artista.slug = new_slug

        artista.bio = request.form.get('bio') or None
        artista.is_band = request.form.get('is_band') == 'on'

        # Social links
        artista.instagram = request.form.get('instagram') or None
        artista.facebook = request.form.get('facebook') or None
        artista.twitter = request.form.get('twitter') or None
        artista.spotify = request.form.get('spotify') or None
        artista.youtube = request.form.get('youtube') or None
        artista.apple_music = request.form.get('apple_music') or None
        artista.website = request.form.get('website') or None
        artista.email = request.form.get('email_artista') or None

        # Metadati
        artista.genere = request.form.get('genere') or None
        anno_fondazione = request.form.get('anno_fondazione') or None
        artista.anno_fondazione = int(anno_fondazione) if anno_fondazione else None
        artista.paese = request.form.get('paese') or None
        artista.citta = request.form.get('citta') or None

        # Stato
        artista.ordine = int(request.form.get('ordine') or 0)
        artista.attivo = request.form.get('attivo') == 'on'
        artista.in_evidenza = request.form.get('in_evidenza') == 'on'

        # Gestione upload foto
        if 'foto' in request.files:
            file = request.files['foto']
            if file and file.filename:
                new_foto = save_uploaded_file(file)
                if new_foto:
                    delete_uploaded_file(artista.foto)
                    artista.foto = new_foto
                else:
                    flash('Formato immagine non valido.', 'warning')

        if request.form.get('rimuovi_foto') == 'on':
            delete_uploaded_file(artista.foto)
            artista.foto = None

        # Gestione upload foto copertina
        if 'foto_copertina' in request.files:
            file = request.files['foto_copertina']
            if file and file.filename:
                new_foto = save_uploaded_file(file)
                if new_foto:
                    delete_uploaded_file(artista.foto_copertina)
                    artista.foto_copertina = new_foto
                else:
                    flash('Formato immagine copertina non valido.', 'warning')

        if request.form.get('rimuovi_foto_copertina') == 'on':
            delete_uploaded_file(artista.foto_copertina)
            artista.foto_copertina = None

        artista.save()

        flash('Artista modificato con successo.', 'success')
        return redirect(url_for('lista_artisti'))

    account_artista = artista.get_utente()
    return render_template('admin/artista_form.html', artista=artista, membri=membri, dischi=dischi, eventi=eventi, account_artista=account_artista)


@app.route('/admin/artisti/<int:id>/elimina', methods=['POST'])
@login_required
@permesso_menu_required
def elimina_artista(id):
    artista = Artista.get_by_id(id)
    if not artista:
        flash('Artista non trovato.', 'danger')
        return redirect(url_for('lista_artisti'))

    # Elimina le immagini associate
    delete_uploaded_file(artista.foto)
    delete_uploaded_file(artista.foto_copertina)

    artista.delete()
    flash('Artista eliminato con successo.', 'success')
    return redirect(url_for('lista_artisti'))


@app.route('/admin/artisti/<int:id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_password_artista(id):
    artista = Artista.get_by_id(id)
    if not artista:
        flash('Artista non trovato.', 'danger')
        return redirect(url_for('lista_artisti'))

    account = artista.get_utente()
    if not account:
        flash('Questo artista non ha un account associato.', 'warning')
        return redirect(url_for('modifica_artista', id=id))

    import secrets
    import string
    alphabet = string.ascii_letters + string.digits
    nuova_password = ''.join(secrets.choice(alphabet) for _ in range(12))
    account.set_password(nuova_password)
    account.save()

    session['credenziali_artista'] = {'username': account.username, 'password': nuova_password}
    return redirect(url_for('credenziali_artista', id=id))


@app.route('/admin/artisti/<int:id>/credenziali')
@login_required
@admin_required
def credenziali_artista(id):
    artista = Artista.get_by_id(id)
    if not artista:
        flash('Artista non trovato.', 'danger')
        return redirect(url_for('lista_artisti'))

    cred = session.pop('credenziali_artista', None)
    if not cred:
        flash('Nessuna credenziale da visualizzare.', 'warning')
        return redirect(url_for('modifica_artista', id=id))

    from datetime import datetime
    return render_template('admin/credenziali_artista.html',
        artista=artista,
        username=cred['username'],
        password=cred['password'],
        data_generazione=datetime.now().strftime('%d/%m/%Y alle %H:%M')
    )


# ============ ROUTES ADMIN MEMBRI BAND ============

@app.route('/admin/artisti/<int:artista_id>/membri/nuovo', methods=['GET', 'POST'])
@login_required
@permesso_menu_required
def nuovo_membro(artista_id):
    artista = Artista.get_by_id(artista_id)
    if not artista:
        flash('Artista non trovato.', 'danger')
        return redirect(url_for('lista_artisti'))

    if not artista.is_band:
        flash('Puoi aggiungere membri solo a una band.', 'warning')
        return redirect(url_for('modifica_artista', id=artista_id))

    if request.method == 'POST':
        nome = request.form.get('nome')
        cognome = request.form.get('cognome') or None
        nome_arte = request.form.get('nome_arte') or None
        ruolo = request.form.get('ruolo')
        bio_breve = request.form.get('bio_breve') or None
        attivo = request.form.get('attivo') == 'on'
        ordine = int(request.form.get('ordine') or 0)

        # Date
        data_ingresso = request.form.get('data_ingresso') or None
        if data_ingresso:
            data_ingresso = datetime.strptime(data_ingresso, '%Y-%m-%d').date()
        data_uscita = request.form.get('data_uscita') or None
        if data_uscita:
            data_uscita = datetime.strptime(data_uscita, '%Y-%m-%d').date()

        # Gestione upload foto
        foto = None
        if 'foto' in request.files:
            file = request.files['foto']
            if file and file.filename:
                foto = save_uploaded_file(file)
                if not foto and file.filename:
                    flash('Formato immagine non valido.', 'warning')

        membro = MembroBand(
            artista_id=artista_id,
            nome=nome,
            cognome=cognome,
            nome_arte=nome_arte,
            ruolo=ruolo,
            foto=foto,
            bio_breve=bio_breve,
            attivo=attivo,
            data_ingresso=data_ingresso,
            data_uscita=data_uscita,
            ordine=ordine
        )
        membro.save()

        flash('Membro aggiunto con successo.', 'success')
        return redirect(url_for('modifica_artista', id=artista_id))

    return render_template('admin/membro_form.html', artista=artista)


@app.route('/admin/membri/<int:id>/modifica', methods=['GET', 'POST'])
@login_required
@permesso_menu_required
def modifica_membro(id):
    membro = MembroBand.get_by_id(id)
    if not membro:
        flash('Membro non trovato.', 'danger')
        return redirect(url_for('lista_artisti'))

    artista = Artista.get_by_id(membro.artista_id)

    if request.method == 'POST':
        membro.nome = request.form.get('nome')
        membro.cognome = request.form.get('cognome') or None
        membro.nome_arte = request.form.get('nome_arte') or None
        membro.ruolo = request.form.get('ruolo')
        membro.bio_breve = request.form.get('bio_breve') or None
        membro.attivo = request.form.get('attivo') == 'on'
        membro.ordine = int(request.form.get('ordine') or 0)

        # Date
        data_ingresso = request.form.get('data_ingresso') or None
        membro.data_ingresso = datetime.strptime(data_ingresso, '%Y-%m-%d').date() if data_ingresso else None
        data_uscita = request.form.get('data_uscita') or None
        membro.data_uscita = datetime.strptime(data_uscita, '%Y-%m-%d').date() if data_uscita else None

        # Gestione upload foto
        if 'foto' in request.files:
            file = request.files['foto']
            if file and file.filename:
                new_foto = save_uploaded_file(file)
                if new_foto:
                    delete_uploaded_file(membro.foto)
                    membro.foto = new_foto
                else:
                    flash('Formato immagine non valido.', 'warning')

        if request.form.get('rimuovi_foto') == 'on':
            delete_uploaded_file(membro.foto)
            membro.foto = None

        membro.save()

        flash('Membro modificato con successo.', 'success')
        return redirect(url_for('modifica_artista', id=membro.artista_id))

    return render_template('admin/membro_form.html', membro=membro, artista=artista)


@app.route('/admin/membri/<int:id>/elimina', methods=['POST'])
@login_required
@permesso_menu_required
def elimina_membro(id):
    membro = MembroBand.get_by_id(id)
    if not membro:
        flash('Membro non trovato.', 'danger')
        return redirect(url_for('lista_artisti'))

    artista_id = membro.artista_id
    delete_uploaded_file(membro.foto)
    membro.delete()

    flash('Membro eliminato con successo.', 'success')
    return redirect(url_for('modifica_artista', id=artista_id))


# ============ ROUTES ADMIN DISCHI ============

@app.route('/admin/dischi')
@login_required
@permesso_menu_required
def lista_dischi():
    dischi = Disco.get_all()
    return render_template('admin/dischi.html', dischi=dischi)


@app.route('/admin/dischi/nuovo', methods=['GET', 'POST'])
@login_required
@permesso_menu_required
def nuovo_disco():
    artisti = Artista.get_all_active()

    if request.method == 'POST':
        artista_id = int(request.form.get('artista_id'))
        titolo = request.form.get('titolo')
        slug = request.form.get('slug') or genera_slug(titolo)
        tipo = request.form.get('tipo') or 'album'
        descrizione = request.form.get('descrizione') or None

        # Date
        anno_uscita = request.form.get('anno_uscita') or None
        if anno_uscita:
            anno_uscita = int(anno_uscita)
        data_uscita = request.form.get('data_uscita') or None
        if data_uscita:
            data_uscita = datetime.strptime(data_uscita, '%Y-%m-%d').date()

        etichetta = request.form.get('etichetta') or None
        formato = request.form.get('formato') or None

        # Link streaming
        link_spotify = request.form.get('link_spotify') or None
        link_apple_music = request.form.get('link_apple_music') or None
        link_youtube_music = request.form.get('link_youtube_music') or None
        link_amazon_music = request.form.get('link_amazon_music') or None
        link_deezer = request.form.get('link_deezer') or None
        link_tidal = request.form.get('link_tidal') or None
        link_acquisto = request.form.get('link_acquisto') or None

        # Stato
        ordine = int(request.form.get('ordine') or 0)
        pubblicato = request.form.get('pubblicato') == 'on'
        in_evidenza = request.form.get('in_evidenza') == 'on'

        # Verifica slug univoco
        existing = Disco.get_by_slug(slug)
        if existing:
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"

        # Gestione upload copertina
        copertina = None
        if 'copertina' in request.files:
            file = request.files['copertina']
            if file and file.filename:
                copertina = save_uploaded_file(file)
                if not copertina and file.filename:
                    flash('Formato immagine non valido.', 'warning')

        disco = Disco(
            artista_id=artista_id,
            titolo=titolo,
            slug=slug,
            tipo=tipo,
            copertina=copertina,
            anno_uscita=anno_uscita,
            data_uscita=data_uscita,
            etichetta=etichetta,
            formato=formato,
            descrizione=descrizione,
            link_spotify=link_spotify,
            link_apple_music=link_apple_music,
            link_youtube_music=link_youtube_music,
            link_amazon_music=link_amazon_music,
            link_deezer=link_deezer,
            link_tidal=link_tidal,
            link_acquisto=link_acquisto,
            pubblicato=pubblicato,
            in_evidenza=in_evidenza,
            ordine=ordine
        )
        disco.save()

        flash('Disco creato con successo.', 'success')
        return redirect(url_for('lista_dischi'))

    return render_template('admin/disco_form.html', artisti=artisti)


@app.route('/admin/dischi/<int:id>/modifica', methods=['GET', 'POST'])
@login_required
@permesso_menu_required
def modifica_disco(id):
    disco = Disco.get_by_id(id)
    if not disco:
        flash('Disco non trovato.', 'danger')
        return redirect(url_for('lista_dischi'))

    artisti = Artista.get_all_active()
    brani = disco.get_brani()

    if request.method == 'POST':
        disco.artista_id = int(request.form.get('artista_id'))
        disco.titolo = request.form.get('titolo')

        new_slug = request.form.get('slug') or genera_slug(disco.titolo)
        existing = Disco.get_by_slug(new_slug)
        if existing and existing.id != disco.id:
            new_slug = f"{new_slug}-{uuid.uuid4().hex[:6]}"
        disco.slug = new_slug

        disco.tipo = request.form.get('tipo') or 'album'
        disco.descrizione = request.form.get('descrizione') or None

        # Date
        anno_uscita = request.form.get('anno_uscita') or None
        disco.anno_uscita = int(anno_uscita) if anno_uscita else None
        data_uscita = request.form.get('data_uscita') or None
        disco.data_uscita = datetime.strptime(data_uscita, '%Y-%m-%d').date() if data_uscita else None

        disco.etichetta = request.form.get('etichetta') or None
        disco.formato = request.form.get('formato') or None

        # Link streaming
        disco.link_spotify = request.form.get('link_spotify') or None
        disco.link_apple_music = request.form.get('link_apple_music') or None
        disco.link_youtube_music = request.form.get('link_youtube_music') or None
        disco.link_amazon_music = request.form.get('link_amazon_music') or None
        disco.link_deezer = request.form.get('link_deezer') or None
        disco.link_tidal = request.form.get('link_tidal') or None
        disco.link_acquisto = request.form.get('link_acquisto') or None

        # Stato
        disco.ordine = int(request.form.get('ordine') or 0)
        disco.pubblicato = request.form.get('pubblicato') == 'on'
        disco.in_evidenza = request.form.get('in_evidenza') == 'on'

        # Gestione upload copertina
        if 'copertina' in request.files:
            file = request.files['copertina']
            if file and file.filename:
                new_copertina = save_uploaded_file(file)
                if new_copertina:
                    delete_uploaded_file(disco.copertina)
                    disco.copertina = new_copertina
                else:
                    flash('Formato immagine non valido.', 'warning')

        if request.form.get('rimuovi_copertina') == 'on':
            delete_uploaded_file(disco.copertina)
            disco.copertina = None

        disco.save()

        flash('Disco modificato con successo.', 'success')
        return redirect(url_for('lista_dischi'))

    return render_template('admin/disco_form.html', disco=disco, artisti=artisti, brani=brani)


@app.route('/admin/dischi/<int:id>/elimina', methods=['POST'])
@login_required
@permesso_menu_required
def elimina_disco(id):
    disco = Disco.get_by_id(id)
    if not disco:
        flash('Disco non trovato.', 'danger')
        return redirect(url_for('lista_dischi'))

    delete_uploaded_file(disco.copertina)
    disco.delete()

    flash('Disco eliminato con successo.', 'success')
    return redirect(url_for('lista_dischi'))


# ============ ROUTES ADMIN BRANI ============

@app.route('/admin/brani')
@login_required
@permesso_menu_required
def lista_brani():
    brani = Brano.get_all()
    return render_template('admin/brani.html', brani=brani)


@app.route('/admin/brani/nuovo', methods=['GET', 'POST'])
@login_required
@permesso_menu_required
def nuovo_brano():
    artisti = Artista.get_all_active()
    dischi = Disco.get_all()

    if request.method == 'POST':
        artista_id = int(request.form.get('artista_id'))
        disco_id = request.form.get('disco_id') or None
        if disco_id:
            disco_id = int(disco_id)

        titolo = request.form.get('titolo')
        slug = request.form.get('slug') or genera_slug(titolo)
        durata = request.form.get('durata') or None
        numero_traccia = request.form.get('numero_traccia') or None
        if numero_traccia:
            numero_traccia = int(numero_traccia)

        featuring = request.form.get('featuring') or None
        produttore = request.form.get('produttore') or None
        autori = request.form.get('autori') or None
        genere = request.form.get('genere') or None
        anno = request.form.get('anno') or None
        if anno:
            anno = int(anno)
        isrc = request.form.get('isrc') or None

        # Link
        link_spotify = request.form.get('link_spotify') or None
        link_apple_music = request.form.get('link_apple_music') or None
        link_youtube = request.form.get('link_youtube') or None
        link_youtube_music = request.form.get('link_youtube_music') or None
        link_soundcloud = request.form.get('link_soundcloud') or None
        link_altro = request.form.get('link_altro') or None

        testo = request.form.get('testo') or None
        video_ufficiale = request.form.get('video_ufficiale') or None

        # Stato
        pubblicato = request.form.get('pubblicato') == 'on'
        is_singolo = request.form.get('is_singolo') == 'on'
        data_uscita = request.form.get('data_uscita') or None
        if data_uscita:
            data_uscita = datetime.strptime(data_uscita, '%Y-%m-%d').date()

        # Verifica slug univoco
        existing = Brano.get_by_slug(slug)
        if existing:
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"

        brano = Brano(
            disco_id=disco_id,
            artista_id=artista_id,
            titolo=titolo,
            slug=slug,
            durata=durata,
            numero_traccia=numero_traccia,
            featuring=featuring,
            produttore=produttore,
            autori=autori,
            genere=genere,
            anno=anno,
            isrc=isrc,
            link_spotify=link_spotify,
            link_apple_music=link_apple_music,
            link_youtube=link_youtube,
            link_youtube_music=link_youtube_music,
            link_soundcloud=link_soundcloud,
            link_altro=link_altro,
            testo=testo,
            video_ufficiale=video_ufficiale,
            pubblicato=pubblicato,
            is_singolo=is_singolo,
            data_uscita=data_uscita
        )
        brano.save()

        flash('Brano creato con successo.', 'success')
        return redirect(url_for('lista_brani'))

    return render_template('admin/brano_form.html', artisti=artisti, dischi=dischi)


@app.route('/admin/brani/<int:id>/modifica', methods=['GET', 'POST'])
@login_required
@permesso_menu_required
def modifica_brano(id):
    brano = Brano.get_by_id(id)
    if not brano:
        flash('Brano non trovato.', 'danger')
        return redirect(url_for('lista_brani'))

    artisti = Artista.get_all_active()
    dischi = Disco.get_all()

    if request.method == 'POST':
        brano.artista_id = int(request.form.get('artista_id'))
        disco_id = request.form.get('disco_id') or None
        brano.disco_id = int(disco_id) if disco_id else None

        brano.titolo = request.form.get('titolo')
        new_slug = request.form.get('slug') or genera_slug(brano.titolo)
        existing = Brano.get_by_slug(new_slug)
        if existing and existing.id != brano.id:
            new_slug = f"{new_slug}-{uuid.uuid4().hex[:6]}"
        brano.slug = new_slug

        brano.durata = request.form.get('durata') or None
        numero_traccia = request.form.get('numero_traccia') or None
        brano.numero_traccia = int(numero_traccia) if numero_traccia else None

        brano.featuring = request.form.get('featuring') or None
        brano.produttore = request.form.get('produttore') or None
        brano.autori = request.form.get('autori') or None
        brano.genere = request.form.get('genere') or None
        anno = request.form.get('anno') or None
        brano.anno = int(anno) if anno else None
        brano.isrc = request.form.get('isrc') or None

        # Link
        brano.link_spotify = request.form.get('link_spotify') or None
        brano.link_apple_music = request.form.get('link_apple_music') or None
        brano.link_youtube = request.form.get('link_youtube') or None
        brano.link_youtube_music = request.form.get('link_youtube_music') or None
        brano.link_soundcloud = request.form.get('link_soundcloud') or None
        brano.link_altro = request.form.get('link_altro') or None

        brano.testo = request.form.get('testo') or None
        brano.video_ufficiale = request.form.get('video_ufficiale') or None

        # Stato
        brano.pubblicato = request.form.get('pubblicato') == 'on'
        brano.is_singolo = request.form.get('is_singolo') == 'on'
        data_uscita = request.form.get('data_uscita') or None
        brano.data_uscita = datetime.strptime(data_uscita, '%Y-%m-%d').date() if data_uscita else None

        brano.save()

        flash('Brano modificato con successo.', 'success')
        return redirect(url_for('lista_brani'))

    return render_template('admin/brano_form.html', brano=brano, artisti=artisti, dischi=dischi)


@app.route('/admin/brani/<int:id>/elimina', methods=['POST'])
@login_required
@permesso_menu_required
def elimina_brano(id):
    brano = Brano.get_by_id(id)
    if not brano:
        flash('Brano non trovato.', 'danger')
        return redirect(url_for('lista_brani'))

    brano.delete()
    flash('Brano eliminato con successo.', 'success')
    return redirect(url_for('lista_brani'))


# ============ ROUTES ADMIN EVENTI ============

@app.route('/admin/eventi')
@login_required
@permesso_menu_required
def lista_eventi():
    eventi = Evento.get_all()
    return render_template('admin/eventi.html', eventi=eventi)


@app.route('/admin/eventi/nuovo', methods=['GET', 'POST'])
@login_required
@permesso_menu_required
def nuovo_evento():
    artisti = Artista.get_all_active()

    if request.method == 'POST':
        artista_id = int(request.form.get('artista_id'))
        titolo = request.form.get('titolo')
        slug = request.form.get('slug') or genera_slug(titolo)
        tipo = request.form.get('tipo') or 'concerto'
        descrizione = request.form.get('descrizione') or None

        # Data e ora
        data_evento = request.form.get('data_evento')
        data_evento = datetime.strptime(data_evento, '%Y-%m-%d').date()
        ora_inizio = request.form.get('ora_inizio') or None
        if ora_inizio:
            ora_inizio = datetime.strptime(ora_inizio, '%H:%M').time()
        ora_fine = request.form.get('ora_fine') or None
        if ora_fine:
            ora_fine = datetime.strptime(ora_fine, '%H:%M').time()

        # Location
        venue = request.form.get('venue') or None
        citta = request.form.get('citta')
        paese = request.form.get('paese') or 'Italia'
        indirizzo = request.form.get('indirizzo') or None
        coordinate_gps = request.form.get('coordinate_gps') or None

        # Biglietti
        link_biglietti = request.form.get('link_biglietti') or None
        prezzo_da = request.form.get('prezzo_da') or None
        if prezzo_da:
            prezzo_da = float(prezzo_da)
        prezzo_a = request.form.get('prezzo_a') or None
        if prezzo_a:
            prezzo_a = float(prezzo_a)
        sold_out = request.form.get('sold_out') == 'on'

        # Stato
        stato = request.form.get('stato') or 'programmato'
        pubblicato = request.form.get('pubblicato') == 'on'
        in_evidenza = request.form.get('in_evidenza') == 'on'

        # Verifica slug univoco
        existing = Evento.get_by_slug(slug)
        if existing:
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"

        # Gestione upload immagine
        immagine = None
        if 'immagine' in request.files:
            file = request.files['immagine']
            if file and file.filename:
                immagine = save_uploaded_file(file)
                if not immagine and file.filename:
                    flash('Formato immagine non valido.', 'warning')

        evento = Evento(
            artista_id=artista_id,
            titolo=titolo,
            slug=slug,
            tipo=tipo,
            descrizione=descrizione,
            immagine=immagine,
            data_evento=data_evento,
            ora_inizio=ora_inizio,
            ora_fine=ora_fine,
            venue=venue,
            citta=citta,
            paese=paese,
            indirizzo=indirizzo,
            coordinate_gps=coordinate_gps,
            link_biglietti=link_biglietti,
            prezzo_da=prezzo_da,
            prezzo_a=prezzo_a,
            sold_out=sold_out,
            stato=stato,
            pubblicato=pubblicato,
            in_evidenza=in_evidenza
        )
        evento.save()

        flash('Evento creato con successo.', 'success')
        return redirect(url_for('lista_eventi'))

    return render_template('admin/evento_form.html', artisti=artisti)


@app.route('/admin/eventi/<int:id>/modifica', methods=['GET', 'POST'])
@login_required
@permesso_menu_required
def modifica_evento(id):
    evento = Evento.get_by_id(id)
    if not evento:
        flash('Evento non trovato.', 'danger')
        return redirect(url_for('lista_eventi'))

    artisti = Artista.get_all_active()

    if request.method == 'POST':
        evento.artista_id = int(request.form.get('artista_id'))
        evento.titolo = request.form.get('titolo')

        new_slug = request.form.get('slug') or genera_slug(evento.titolo)
        existing = Evento.get_by_slug(new_slug)
        if existing and existing.id != evento.id:
            new_slug = f"{new_slug}-{uuid.uuid4().hex[:6]}"
        evento.slug = new_slug

        evento.tipo = request.form.get('tipo') or 'concerto'
        evento.descrizione = request.form.get('descrizione') or None

        # Data e ora
        data_evento = request.form.get('data_evento')
        evento.data_evento = datetime.strptime(data_evento, '%Y-%m-%d').date()
        ora_inizio = request.form.get('ora_inizio') or None
        evento.ora_inizio = datetime.strptime(ora_inizio, '%H:%M').time() if ora_inizio else None
        ora_fine = request.form.get('ora_fine') or None
        evento.ora_fine = datetime.strptime(ora_fine, '%H:%M').time() if ora_fine else None

        # Location
        evento.venue = request.form.get('venue') or None
        evento.citta = request.form.get('citta')
        evento.paese = request.form.get('paese') or 'Italia'
        evento.indirizzo = request.form.get('indirizzo') or None
        evento.coordinate_gps = request.form.get('coordinate_gps') or None

        # Biglietti
        evento.link_biglietti = request.form.get('link_biglietti') or None
        prezzo_da = request.form.get('prezzo_da') or None
        evento.prezzo_da = float(prezzo_da) if prezzo_da else None
        prezzo_a = request.form.get('prezzo_a') or None
        evento.prezzo_a = float(prezzo_a) if prezzo_a else None
        evento.sold_out = request.form.get('sold_out') == 'on'

        # Stato
        evento.stato = request.form.get('stato') or 'programmato'
        evento.pubblicato = request.form.get('pubblicato') == 'on'
        evento.in_evidenza = request.form.get('in_evidenza') == 'on'

        # Gestione upload immagine
        if 'immagine' in request.files:
            file = request.files['immagine']
            if file and file.filename:
                new_immagine = save_uploaded_file(file)
                if new_immagine:
                    delete_uploaded_file(evento.immagine)
                    evento.immagine = new_immagine
                else:
                    flash('Formato immagine non valido.', 'warning')

        if request.form.get('rimuovi_immagine') == 'on':
            delete_uploaded_file(evento.immagine)
            evento.immagine = None

        evento.save()

        flash('Evento modificato con successo.', 'success')
        return redirect(url_for('lista_eventi'))

    return render_template('admin/evento_form.html', evento=evento, artisti=artisti)


@app.route('/admin/eventi/<int:id>/elimina', methods=['POST'])
@login_required
@permesso_menu_required
def elimina_evento(id):
    evento = Evento.get_by_id(id)
    if not evento:
        flash('Evento non trovato.', 'danger')
        return redirect(url_for('lista_eventi'))

    delete_uploaded_file(evento.immagine)
    evento.delete()

    flash('Evento eliminato con successo.', 'success')
    return redirect(url_for('lista_eventi'))


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
        print('Utente admin creato (password: admin123)')

    # Crea voci menu mancanti (aggiunge solo quelle che non esistono gia)
    menu_default = [
        ('Dashboard', 'bi-speedometer2', '/dashboard', 0),
        ('Utenti', 'bi-people', '/admin/utenti', 1),
        ('Gestione Menu', 'bi-list-ul', '/admin/menu', 2),
        ('Servizi', 'bi-briefcase', '/admin/servizi', 3),
        ('Categorie Servizi', 'bi-folder', '/admin/categorie-servizi', 4),
        ('News', 'bi-newspaper', '/admin/news', 5),
        ('Artisti', 'bi-people-fill', '/admin/artisti', 10),
        ('Discografia', 'bi-disc-fill', '/admin/dischi', 11),
        ('Brani', 'bi-music-note-beamed', '/admin/brani', 12),
        ('Eventi', 'bi-calendar-event-fill', '/admin/eventi', 13),
    ]

    conn = get_db_connection()
    cursor = conn.cursor()
    for nome, icona, url, ordine in menu_default:
        cursor.execute('SELECT id FROM menu WHERE url = %s', (url,))
        if not cursor.fetchone():
            cursor.execute(
                'INSERT INTO menu (nome, icona, url, ordine, attivo) VALUES (%s, %s, %s, %s, TRUE)',
                (nome, icona, url, ordine)
            )
            print(f'Menu aggiunto: {nome}')
    conn.commit()
    cursor.close()
    conn.close()


# ============ PORTALE ARTISTA ============

@app.route('/artista/dashboard')
@login_required
@artista_required
def artista_dashboard():
    artista = current_user.get_artista()
    if not artista:
        flash('Profilo artista non trovato.', 'danger')
        return redirect(url_for('dashboard'))

    dischi = artista.get_dischi()
    brani = artista.get_brani()
    eventi = artista.get_eventi()
    eventi_futuri = artista.get_eventi_futuri()

    return render_template('artista/dashboard.html',
                           artista=artista, dischi=dischi, brani=brani,
                           eventi=eventi, eventi_futuri=eventi_futuri)


@app.route('/artista/profilo')
@login_required
@artista_required
def artista_profilo():
    artista = current_user.get_artista()
    if not artista:
        flash('Profilo artista non trovato.', 'danger')
        return redirect(url_for('dashboard'))

    membri = artista.get_membri() if artista.is_band else []
    return render_template('artista/profilo.html', artista=artista, membri=membri)


@app.route('/artista/dischi')
@login_required
@artista_required
def artista_dischi():
    artista = current_user.get_artista()
    if not artista:
        flash('Profilo artista non trovato.', 'danger')
        return redirect(url_for('dashboard'))

    dischi = artista.get_dischi()
    return render_template('artista/dischi.html', artista=artista, dischi=dischi)


@app.route('/artista/dischi/<int:id>')
@login_required
@artista_required
def artista_disco_dettaglio(id):
    artista = current_user.get_artista()
    if not artista:
        flash('Profilo artista non trovato.', 'danger')
        return redirect(url_for('dashboard'))

    disco = Disco.get_by_id(id)
    if not disco or disco.artista_id != artista.id:
        flash('Disco non trovato.', 'danger')
        return redirect(url_for('artista_dischi'))

    brani = disco.get_brani()
    return render_template('artista/disco_dettaglio.html', artista=artista, disco=disco, brani=brani)


@app.route('/artista/brani')
@login_required
@artista_required
def artista_brani():
    artista = current_user.get_artista()
    if not artista:
        flash('Profilo artista non trovato.', 'danger')
        return redirect(url_for('dashboard'))

    brani = artista.get_brani()
    return render_template('artista/brani.html', artista=artista, brani=brani)


@app.route('/artista/eventi')
@login_required
@artista_required
def artista_eventi():
    artista = current_user.get_artista()
    if not artista:
        flash('Profilo artista non trovato.', 'danger')
        return redirect(url_for('dashboard'))

    eventi = artista.get_eventi()
    return render_template('artista/eventi.html', artista=artista, eventi=eventi)


if __name__ == '__main__':
    init_db()
    app.run(debug=True,host="0.0.0.0")
