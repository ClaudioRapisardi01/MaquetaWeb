from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Servizio
from app.forms import ServizioForm
from app.blueprints.auth import admin_required

servizi_bp = Blueprint('servizi', __name__)

@servizi_bp.route('/')
@login_required
def lista():
    servizi = Servizio.query.all()
    return render_template('servizi/lista.html', servizi=servizi)

@servizi_bp.route('/<int:id>')
@login_required
def dettaglio(id):
    servizio = Servizio.query.get_or_404(id)
    return render_template('servizi/dettaglio.html', servizio=servizio)

@servizi_bp.route('/nuovo', methods=['GET', 'POST'])
@login_required
@admin_required
def nuovo():
    form = ServizioForm()
    if form.validate_on_submit():
        servizio = Servizio(
            nome=form.nome.data,
            descrizione=form.descrizione.data,
            categoria=form.categoria.data,
            prezzo=form.prezzo.data,
            valuta=form.valuta.data,
            durata=form.durata.data,
            attivo=form.attivo.data,
            icona=form.icona.data
        )
        db.session.add(servizio)
        db.session.commit()
        flash(f'Servizio {servizio.nome} creato con successo!', 'success')
        return redirect(url_for('servizi.dettaglio', id=servizio.id))
    return render_template('servizi/form.html', form=form, titolo='Nuovo Servizio')

@servizi_bp.route('/<int:id>/modifica', methods=['GET', 'POST'])
@login_required
@admin_required
def modifica(id):
    servizio = Servizio.query.get_or_404(id)
    form = ServizioForm(obj=servizio)
    if form.validate_on_submit():
        servizio.nome = form.nome.data
        servizio.descrizione = form.descrizione.data
        servizio.categoria = form.categoria.data
        servizio.prezzo = form.prezzo.data
        servizio.valuta = form.valuta.data
        servizio.durata = form.durata.data
        servizio.attivo = form.attivo.data
        servizio.icona = form.icona.data
        db.session.commit()
        flash(f'Servizio {servizio.nome} aggiornato!', 'success')
        return redirect(url_for('servizi.dettaglio', id=servizio.id))
    return render_template('servizi/form.html', form=form, titolo='Modifica Servizio', servizio=servizio)

@servizi_bp.route('/<int:id>/elimina')
@login_required
@admin_required
def elimina(id):
    servizio = Servizio.query.get_or_404(id)
    nome = servizio.nome
    db.session.delete(servizio)
    db.session.commit()
    flash(f'Servizio {nome} eliminato.', 'success')
    return redirect(url_for('servizi.lista'))
