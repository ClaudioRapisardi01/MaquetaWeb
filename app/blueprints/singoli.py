from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Singolo, Artista
from app.forms import SingoloForm
from app.blueprints.auth import editor_required
from app.blueprints.artisti import salva_immagine

singoli_bp = Blueprint('singoli', __name__)

@singoli_bp.route('/')
@login_required
def lista():
    page = request.args.get('page', 1, type=int)
    query = Singolo.query
    if not current_user.is_editor():
        query = query.filter_by(creato_da=current_user.id)
    singoli = query.order_by(Singolo.data_creazione.desc()).paginate(page=page, per_page=12, error_out=False)
    return render_template('singoli/lista.html', singoli=singoli)

@singoli_bp.route('/<int:id>')
@login_required
def dettaglio(id):
    singolo = Singolo.query.get_or_404(id)
    if not current_user.is_editor() and singolo.creato_da != current_user.id:
        flash('Non hai permesso di visualizzare questo singolo.', 'danger')
        return redirect(url_for('singoli.lista'))
    return render_template('singoli/dettaglio.html', singolo=singolo)

@singoli_bp.route('/nuovo', methods=['GET', 'POST'])
@login_required
@editor_required
def nuovo():
    form = SingoloForm()
    artisti = Artista.query.filter_by(attivo=True).all()

    if form.validate_on_submit():
        singolo = Singolo(
            titolo=form.titolo.data,
            descrizione=form.descrizione.data,
            data_uscita=form.data_uscita.data,
            durata=form.durata.data,
            genere=form.genere.data,
            etichetta=form.etichetta.data,
            isrc=form.isrc.data,
            link_spotify=form.link_spotify.data,
            link_apple_music=form.link_apple_music.data,
            link_youtube=form.link_youtube.data,
            creato_da=current_user.id
        )

        if form.copertina.data:
            singolo.copertina = salva_immagine(form.copertina.data)

        artisti_ids = request.form.getlist('artisti')
        for artista_id in artisti_ids:
            artista = Artista.query.get(int(artista_id))
            if artista:
                singolo.artisti.append(artista)

        db.session.add(singolo)
        db.session.commit()
        flash(f'Singolo {singolo.titolo} creato con successo!', 'success')
        return redirect(url_for('singoli.dettaglio', id=singolo.id))

    return render_template('singoli/form.html', form=form, titolo='Nuovo Singolo', artisti=artisti)

@singoli_bp.route('/<int:id>/modifica', methods=['GET', 'POST'])
@login_required
def modifica(id):
    singolo = Singolo.query.get_or_404(id)
    if not current_user.is_editor() and singolo.creato_da != current_user.id:
        flash('Non hai permesso di modificare questo singolo.', 'danger')
        return redirect(url_for('singoli.lista'))

    form = SingoloForm(obj=singolo)
    artisti = Artista.query.filter_by(attivo=True).all()

    if form.validate_on_submit():
        singolo.titolo = form.titolo.data
        singolo.descrizione = form.descrizione.data
        singolo.data_uscita = form.data_uscita.data
        singolo.durata = form.durata.data
        singolo.genere = form.genere.data
        singolo.etichetta = form.etichetta.data
        singolo.isrc = form.isrc.data
        singolo.link_spotify = form.link_spotify.data
        singolo.link_apple_music = form.link_apple_music.data
        singolo.link_youtube = form.link_youtube.data

        if form.copertina.data:
            singolo.copertina = salva_immagine(form.copertina.data)

        singolo.artisti = []
        artisti_ids = request.form.getlist('artisti')
        for artista_id in artisti_ids:
            artista = Artista.query.get(int(artista_id))
            if artista:
                singolo.artisti.append(artista)

        db.session.commit()
        flash(f'Singolo {singolo.titolo} aggiornato!', 'success')
        return redirect(url_for('singoli.dettaglio', id=singolo.id))

    return render_template('singoli/form.html', form=form, titolo='Modifica Singolo', singolo=singolo, artisti=artisti)

@singoli_bp.route('/<int:id>/elimina')
@login_required
@editor_required
def elimina(id):
    singolo = Singolo.query.get_or_404(id)
    titolo = singolo.titolo
    db.session.delete(singolo)
    db.session.commit()
    flash(f'Singolo {titolo} eliminato.', 'success')
    return redirect(url_for('singoli.lista'))
