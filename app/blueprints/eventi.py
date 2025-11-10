from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Evento
from app.forms import EventoForm
from app.blueprints.auth import editor_required
from datetime import datetime

eventi_bp = Blueprint('eventi', __name__)

@eventi_bp.route('/')
@login_required
def lista():
    page = request.args.get('page', 1, type=int)
    query = Evento.query
    if not current_user.is_editor():
        query = query.filter_by(creato_da=current_user.id)
    eventi = query.order_by(Evento.data_inizio.desc()).paginate(page=page, per_page=12, error_out=False)
    return render_template('eventi/lista.html', eventi=eventi)

@eventi_bp.route('/<int:id>')
@login_required
def dettaglio(id):
    evento = Evento.query.get_or_404(id)
    if not current_user.is_editor() and evento.creato_da != current_user.id:
        flash('Non hai permesso di visualizzare questo evento.', 'danger')
        return redirect(url_for('eventi.lista'))
    return render_template('eventi/dettaglio.html', evento=evento)

@eventi_bp.route('/nuovo', methods=['GET', 'POST'])
@login_required
@editor_required
def nuovo():
    form = EventoForm()
    if form.validate_on_submit():
        evento = Evento(
            titolo=form.titolo.data,
            descrizione=form.descrizione.data,
            tipo=form.tipo.data,
            data_inizio=form.data_inizio.data,
            data_fine=form.data_fine.data,
            luogo=form.luogo.data,
            indirizzo=form.indirizzo.data,
            citta=form.citta.data,
            paese=form.paese.data,
            visibilita=form.visibilita.data,
            note=form.note.data,
            creato_da=current_user.id
        )
        db.session.add(evento)
        db.session.commit()
        flash(f'Evento {evento.titolo} creato con successo!', 'success')
        return redirect(url_for('eventi.dettaglio', id=evento.id))
    return render_template('eventi/form.html', form=form, titolo='Nuovo Evento')

@eventi_bp.route('/<int:id>/modifica', methods=['GET', 'POST'])
@login_required
def modifica(id):
    evento = Evento.query.get_or_404(id)
    if not current_user.is_editor() and evento.creato_da != current_user.id:
        flash('Non hai permesso di modificare questo evento.', 'danger')
        return redirect(url_for('eventi.lista'))

    form = EventoForm(obj=evento)
    if form.validate_on_submit():
        evento.titolo = form.titolo.data
        evento.descrizione = form.descrizione.data
        evento.tipo = form.tipo.data
        evento.data_inizio = form.data_inizio.data
        evento.data_fine = form.data_fine.data
        evento.luogo = form.luogo.data
        evento.indirizzo = form.indirizzo.data
        evento.citta = form.citta.data
        evento.paese = form.paese.data
        evento.visibilita = form.visibilita.data
        evento.note = form.note.data
        db.session.commit()
        flash(f'Evento {evento.titolo} aggiornato!', 'success')
        return redirect(url_for('eventi.dettaglio', id=evento.id))
    return render_template('eventi/form.html', form=form, titolo='Modifica Evento', evento=evento)

@eventi_bp.route('/<int:id>/elimina')
@login_required
@editor_required
def elimina(id):
    evento = Evento.query.get_or_404(id)
    titolo = evento.titolo
    db.session.delete(evento)
    db.session.commit()
    flash(f'Evento {titolo} eliminato.', 'success')
    return redirect(url_for('eventi.lista'))
