from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from database import init_database, get_db_connection
from models import Utente, Menu, Permesso
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.config.from_object(Config)

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

        # Admin ha tutti i permessi
        for menu in Menu.get_all_active():
            Permesso.set_permesso(admin.id, menu.id, True)

        print('Database inizializzato con utente admin (password: admin123)')


if __name__ == '__main__':
    init_db()
    app.run(debug=True,host="0.0.0.0")
