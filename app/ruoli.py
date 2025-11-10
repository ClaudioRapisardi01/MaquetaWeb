from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models import Ruolo, Permesso, User
from app.forms import RuoloForm

ruoli = Blueprint('ruoli', __name__)


def admin_required(f):
    """Decorator per richiedere permessi admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Accesso negato. Richiesti privilegi di amministratore.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@ruoli.route('/ruoli')
@login_required
@admin_required
def lista():
    page = request.args.get('page', 1, type=int)
    ruoli_list = Ruolo.query.order_by(Ruolo.is_system.desc(), Ruolo.nome).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('ruoli/lista.html', ruoli=ruoli_list)


@ruoli.route('/ruoli/nuovo', methods=['GET', 'POST'])
@login_required
@admin_required
def nuovo():
    form = RuoloForm()

    if form.validate_on_submit():
        ruolo = Ruolo(
            nome=form.nome.data,
            descrizione=form.descrizione.data,
            is_system=False
        )

        # Aggiungi i permessi selezionati
        permessi_ids = request.form.getlist('permessi')
        permessi = Permesso.query.filter(Permesso.id.in_(permessi_ids)).all()
        ruolo.permessi = permessi

        db.session.add(ruolo)
        db.session.commit()
        flash('Ruolo creato con successo!', 'success')
        return redirect(url_for('ruoli.lista'))

    # Carica tutti i permessi raggruppati per modulo
    tutti_permessi = Permesso.query.order_by(Permesso.modulo, Permesso.codice).all()
    permessi_per_modulo = {}
    for permesso in tutti_permessi:
        if permesso.modulo not in permessi_per_modulo:
            permessi_per_modulo[permesso.modulo] = []
        permessi_per_modulo[permesso.modulo].append(permesso)

    return render_template('ruoli/form.html', form=form, titolo='Nuovo Ruolo',
                         permessi_per_modulo=permessi_per_modulo, ruolo=None)


@ruoli.route('/ruoli/<int:id>')
@login_required
@admin_required
def dettaglio(id):
    ruolo = Ruolo.query.get_or_404(id)
    utenti = User.query.filter_by(ruolo_id=id).all()
    return render_template('ruoli/dettaglio.html', ruolo=ruolo, utenti=utenti)


@ruoli.route('/ruoli/<int:id>/modifica', methods=['GET', 'POST'])
@login_required
@admin_required
def modifica(id):
    ruolo = Ruolo.query.get_or_404(id)

    # Non permettere modifica dei ruoli di sistema
    if ruolo.is_system:
        flash('Non puoi modificare i ruoli di sistema.', 'warning')
        return redirect(url_for('ruoli.dettaglio', id=id))

    form = RuoloForm(obj=ruolo)

    if form.validate_on_submit():
        ruolo.nome = form.nome.data
        ruolo.descrizione = form.descrizione.data

        # Aggiorna i permessi selezionati
        permessi_ids = request.form.getlist('permessi')
        permessi = Permesso.query.filter(Permesso.id.in_(permessi_ids)).all()
        ruolo.permessi = permessi

        db.session.commit()
        flash('Ruolo aggiornato con successo!', 'success')
        return redirect(url_for('ruoli.dettaglio', id=id))

    # Carica tutti i permessi raggruppati per modulo
    tutti_permessi = Permesso.query.order_by(Permesso.modulo, Permesso.codice).all()
    permessi_per_modulo = {}
    for permesso in tutti_permessi:
        if permesso.modulo not in permessi_per_modulo:
            permessi_per_modulo[permesso.modulo] = []
        permessi_per_modulo[permesso.modulo].append(permesso)

    # IDs dei permessi già assegnati
    permessi_selezionati = [p.id for p in ruolo.permessi]

    return render_template('ruoli/form.html', form=form, titolo='Modifica Ruolo',
                         permessi_per_modulo=permessi_per_modulo, ruolo=ruolo,
                         permessi_selezionati=permessi_selezionati)


@ruoli.route('/ruoli/<int:id>/elimina', methods=['POST', 'GET'])
@login_required
@admin_required
def elimina(id):
    ruolo = Ruolo.query.get_or_404(id)

    # Non permettere eliminazione dei ruoli di sistema
    if ruolo.is_system:
        flash('Non puoi eliminare i ruoli di sistema.', 'danger')
        return redirect(url_for('ruoli.lista'))

    # Controlla se ci sono utenti con questo ruolo
    utenti_con_ruolo = User.query.filter_by(ruolo_id=id).count()
    if utenti_con_ruolo > 0:
        flash(f'Non puoi eliminare questo ruolo: è assegnato a {utenti_con_ruolo} utent{"e" if utenti_con_ruolo == 1 else "i"}.', 'danger')
        return redirect(url_for('ruoli.dettaglio', id=id))

    db.session.delete(ruolo)
    db.session.commit()
    flash('Ruolo eliminato con successo!', 'success')
    return redirect(url_for('ruoli.lista'))
