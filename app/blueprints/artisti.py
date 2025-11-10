from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Artista
from app.forms import ArtistaForm
from app.blueprints.auth import editor_required
from werkzeug.utils import secure_filename
import os
from datetime import datetime

artisti_bp = Blueprint('artisti', __name__)

def salva_immagine(file, folder='images'):
    if file:
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        filepath = os.path.join('app', 'static', 'uploads', folder, filename)
        file.save(filepath)
        return filename
    return None

@artisti_bp.route('/')
@login_required
def lista():
    page = request.args.get('page', 1, type=int)
    query = Artista.query

    # Filtri per ruolo
    if not current_user.is_editor():
        query = query.filter_by(creato_da=current_user.id)

    artisti = query.order_by(Artista.data_creazione.desc()).paginate(page=page, per_page=12, error_out=False)
    return render_template('artisti/lista.html', artisti=artisti)

@artisti_bp.route('/<int:id>')
@login_required
def dettaglio(id):
    artista = Artista.query.get_or_404(id)

    # Controllo accesso
    if not current_user.is_editor() and artista.creato_da != current_user.id:
        flash('Non hai permesso di visualizzare questo artista.', 'danger')
        return redirect(url_for('artisti.lista'))

    return render_template('artisti/dettaglio.html', artista=artista)

@artisti_bp.route('/nuovo', methods=['GET', 'POST'])
@login_required
@editor_required
def nuovo():
    form = ArtistaForm()
    if form.validate_on_submit():
        artista = Artista(
            nome=form.nome.data,
            nome_arte=form.nome_arte.data,
            biografia=form.biografia.data,
            genere_musicale=form.genere_musicale.data,
            data_nascita=form.data_nascita.data,
            paese=form.paese.data,
            sito_web=form.sito_web.data,
            social_instagram=form.social_instagram.data,
            social_facebook=form.social_facebook.data,
            social_twitter=form.social_twitter.data,
            social_spotify=form.social_spotify.data,
            attivo=form.attivo.data,
            creato_da=current_user.id
        )

        if form.foto.data:
            artista.foto = salva_immagine(form.foto.data)

        db.session.add(artista)
        db.session.commit()
        flash(f'Artista {artista.nome_arte} creato con successo!', 'success')
        return redirect(url_for('artisti.dettaglio', id=artista.id))

    return render_template('artisti/form.html', form=form, titolo='Nuovo Artista')

@artisti_bp.route('/<int:id>/modifica', methods=['GET', 'POST'])
@login_required
def modifica(id):
    artista = Artista.query.get_or_404(id)

    # Controllo permessi
    if not current_user.is_editor() and artista.creato_da != current_user.id:
        flash('Non hai permesso di modificare questo artista.', 'danger')
        return redirect(url_for('artisti.lista'))

    form = ArtistaForm(obj=artista)
    if form.validate_on_submit():
        artista.nome = form.nome.data
        artista.nome_arte = form.nome_arte.data
        artista.biografia = form.biografia.data
        artista.genere_musicale = form.genere_musicale.data
        artista.data_nascita = form.data_nascita.data
        artista.paese = form.paese.data
        artista.sito_web = form.sito_web.data
        artista.social_instagram = form.social_instagram.data
        artista.social_facebook = form.social_facebook.data
        artista.social_twitter = form.social_twitter.data
        artista.social_spotify = form.social_spotify.data
        artista.attivo = form.attivo.data

        if form.foto.data:
            artista.foto = salva_immagine(form.foto.data)

        db.session.commit()
        flash(f'Artista {artista.nome_arte} aggiornato!', 'success')
        return redirect(url_for('artisti.dettaglio', id=artista.id))

    return render_template('artisti/form.html', form=form, titolo='Modifica Artista', artista=artista)

@artisti_bp.route('/<int:id>/elimina')
@login_required
@editor_required
def elimina(id):
    artista = Artista.query.get_or_404(id)
    nome = artista.nome_arte
    db.session.delete(artista)
    db.session.commit()
    flash(f'Artista {nome} eliminato.', 'success')
    return redirect(url_for('artisti.lista'))
