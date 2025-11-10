from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Staff
from app.forms import StaffForm
from app.blueprints.auth import admin_required
from app.blueprints.artisti import salva_immagine

staff_bp = Blueprint('staff', __name__)

@staff_bp.route('/')
@login_required
def lista():
    staff = Staff.query.filter_by(attivo=True).all()
    return render_template('staff/lista.html', staff=staff)

@staff_bp.route('/<int:id>')
@login_required
def dettaglio(id):
    membro = Staff.query.get_or_404(id)
    return render_template('staff/dettaglio.html', membro=membro)

@staff_bp.route('/nuovo', methods=['GET', 'POST'])
@login_required
@admin_required
def nuovo():
    form = StaffForm()
    if form.validate_on_submit():
        membro = Staff(
            nome=form.nome.data,
            cognome=form.cognome.data,
            ruolo=form.ruolo.data,
            email=form.email.data,
            telefono=form.telefono.data,
            biografia=form.biografia.data,
            reparto=form.reparto.data,
            data_assunzione=form.data_assunzione.data,
            attivo=form.attivo.data
        )
        if form.foto.data:
            membro.foto = salva_immagine(form.foto.data)
        db.session.add(membro)
        db.session.commit()
        flash(f'Staff {membro.nome} {membro.cognome} aggiunto con successo!', 'success')
        return redirect(url_for('staff.dettaglio', id=membro.id))
    return render_template('staff/form.html', form=form, titolo='Nuovo Staff')

@staff_bp.route('/<int:id>/modifica', methods=['GET', 'POST'])
@login_required
@admin_required
def modifica(id):
    membro = Staff.query.get_or_404(id)
    form = StaffForm(obj=membro)
    if form.validate_on_submit():
        membro.nome = form.nome.data
        membro.cognome = form.cognome.data
        membro.ruolo = form.ruolo.data
        membro.email = form.email.data
        membro.telefono = form.telefono.data
        membro.biografia = form.biografia.data
        membro.reparto = form.reparto.data
        membro.data_assunzione = form.data_assunzione.data
        membro.attivo = form.attivo.data
        if form.foto.data:
            membro.foto = salva_immagine(form.foto.data)
        db.session.commit()
        flash(f'Staff {membro.nome} {membro.cognome} aggiornato!', 'success')
        return redirect(url_for('staff.dettaglio', id=membro.id))
    return render_template('staff/form.html', form=form, titolo='Modifica Staff', membro=membro)

@staff_bp.route('/<int:id>/elimina')
@login_required
@admin_required
def elimina(id):
    membro = Staff.query.get_or_404(id)
    nome = f'{membro.nome} {membro.cognome}'
    db.session.delete(membro)
    db.session.commit()
    flash(f'Staff {nome} eliminato.', 'success')
    return redirect(url_for('staff.lista'))
