from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Disco, Artista
from app.forms import DiscoForm
from app.blueprints.auth import editor_required
from app.blueprints.artisti import salva_immagine

dischi_bp = Blueprint('dischi', __name__)

@dischi_bp.route('/')
@login_required
def lista():
    page = request.args.get('page', 1, type=int)
    query = Disco.query
    if not current_user.is_editor():
        query = query.filter_by(creato_da=current_user.id)
    dischi = query.order_by(Disco.data_creazione.desc()).paginate(page=page, per_page=12, error_out=False)
    return render_template('dischi/lista.html', dischi=dischi)

@dischi_bp.route('/<int:id>')
@login_required
def dettaglio(id):
    disco = Disco.query.get_or_404(id)
    if not current_user.is_editor() and disco.creato_da != current_user.id:
        flash('Non hai permesso di visualizzare questo disco.', 'danger')
        return redirect(url_for('dischi.lista'))
    return render_template('dischi/dettaglio.html', disco=disco)

@dischi_bp.route('/nuovo', methods=['GET', 'POST'])
@login_required
@editor_required
def nuovo():
    form = DiscoForm()
    artisti = Artista.query.filter_by(attivo=True).all()

    if form.validate_on_submit():
        disco = Disco(
            titolo=form.titolo.data,
            descrizione=form.descrizione.data,
            data_uscita=form.data_uscita.data,
            etichetta=form.etichetta.data,
            numero_tracce=form.numero_tracce.data,
            genere=form.genere.data,
            formato=form.formato.data,
            codice_catalogo=form.codice_catalogo.data,
            link_spotify=form.link_spotify.data,
            link_apple_music=form.link_apple_music.data,
            link_youtube=form.link_youtube.data,
            creato_da=current_user.id
        )

        if form.copertina.data:
            disco.copertina = salva_immagine(form.copertina.data)

        # Aggiungi artisti selezionati
        artisti_ids = request.form.getlist('artisti')
        for artista_id in artisti_ids:
            artista = Artista.query.get(int(artista_id))
            if artista:
                disco.artisti.append(artista)

        db.session.add(disco)
        db.session.commit()
        flash(f'Disco {disco.titolo} creato con successo!', 'success')
        return redirect(url_for('dischi.dettaglio', id=disco.id))

    return render_template('dischi/form.html', form=form, titolo='Nuovo Disco', artisti=artisti)

@dischi_bp.route('/<int:id>/modifica', methods=['GET', 'POST'])
@login_required
def modifica(id):
    disco = Disco.query.get_or_404(id)
    if not current_user.is_editor() and disco.creato_da != current_user.id:
        flash('Non hai permesso di modificare questo disco.', 'danger')
        return redirect(url_for('dischi.lista'))

    form = DiscoForm(obj=disco)
    artisti = Artista.query.filter_by(attivo=True).all()

    if form.validate_on_submit():
        disco.titolo = form.titolo.data
        disco.descrizione = form.descrizione.data
        disco.data_uscita = form.data_uscita.data
        disco.etichetta = form.etichetta.data
        disco.numero_tracce = form.numero_tracce.data
        disco.genere = form.genere.data
        disco.formato = form.formato.data
        disco.codice_catalogo = form.codice_catalogo.data
        disco.link_spotify = form.link_spotify.data
        disco.link_apple_music = form.link_apple_music.data
        disco.link_youtube = form.link_youtube.data

        if form.copertina.data:
            disco.copertina = salva_immagine(form.copertina.data)

        # Aggiorna artisti
        disco.artisti = []
        artisti_ids = request.form.getlist('artisti')
        for artista_id in artisti_ids:
            artista = Artista.query.get(int(artista_id))
            if artista:
                disco.artisti.append(artista)

        db.session.commit()
        flash(f'Disco {disco.titolo} aggiornato!', 'success')
        return redirect(url_for('dischi.dettaglio', id=disco.id))

    return render_template('dischi/form.html', form=form, titolo='Modifica Disco', disco=disco, artisti=artisti)

@dischi_bp.route('/<int:id>/elimina')
@login_required
@editor_required
def elimina(id):
    disco = Disco.query.get_or_404(id)
    titolo = disco.titolo
    db.session.delete(disco)
    db.session.commit()
    flash(f'Disco {titolo} eliminato.', 'success')
    return redirect(url_for('dischi.lista'))
