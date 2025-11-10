from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User
from app.forms import LoginForm, RegistrazioneForm
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Accesso negato. Devi essere un amministratore.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def editor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_editor():
            flash('Accesso negato. Devi avere permessi di editor.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            if not user.attivo:
                flash('Il tuo account è stato disattivato. Contatta l\'amministratore.', 'warning')
                return redirect(url_for('auth.login'))

            login_user(user)
            flash(f'Benvenuto, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash('Username o password non corretti.', 'danger')

    return render_template('auth/login.html', form=form)

@auth_bp.route('/registrazione', methods=['GET', 'POST'])
@login_required
@admin_required
def registrazione():
    form = RegistrazioneForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            ruolo=form.ruolo.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f'Utente {user.username} creato con successo!', 'success')
        return redirect(url_for('auth.lista_utenti'))

    return render_template('auth/registrazione.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout effettuato con successo.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/utenti')
@login_required
@admin_required
def lista_utenti():
    utenti = User.query.all()
    return render_template('auth/lista_utenti.html', utenti=utenti)

@auth_bp.route('/utenti/<int:id>/toggle-attivo')
@login_required
@admin_required
def toggle_attivo(id):
    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        flash('Non puoi disattivare il tuo stesso account!', 'danger')
    else:
        user.attivo = not user.attivo
        db.session.commit()
        stato = 'attivato' if user.attivo else 'disattivato'
        flash(f'Utente {user.username} {stato}.', 'success')
    return redirect(url_for('auth.lista_utenti'))

@auth_bp.route('/utenti/<int:id>/elimina')
@login_required
@admin_required
def elimina_utente(id):
    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        flash('Non puoi eliminare il tuo stesso account!', 'danger')
    else:
        db.session.delete(user)
        db.session.commit()
        flash(f'Utente {user.username} eliminato.', 'success')
    return redirect(url_for('auth.lista_utenti'))
