from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import News
from app.forms import NewsForm
from app.blueprints.auth import editor_required
from app.blueprints.artisti import salva_immagine
from datetime import datetime

news_bp = Blueprint('news', __name__)

@news_bp.route('/')
@login_required
def lista():
    page = request.args.get('page', 1, type=int)
    query = News.query

    # Gli editor vedono tutte le news, gli altri solo le proprie
    if not current_user.is_editor():
        query = query.filter_by(creato_da=current_user.id)

    news = query.order_by(News.data_creazione.desc()).paginate(page=page, per_page=12, error_out=False)
    return render_template('news/lista.html', news=news)

@news_bp.route('/<int:id>')
@login_required
def dettaglio(id):
    articolo = News.query.get_or_404(id)

    if not current_user.is_editor() and articolo.creato_da != current_user.id:
        if not articolo.pubblicata:
            flash('Non hai permesso di visualizzare questa news.', 'danger')
            return redirect(url_for('news.lista'))

    return render_template('news/dettaglio.html', articolo=articolo)

@news_bp.route('/nuova', methods=['GET', 'POST'])
@login_required
@editor_required
def nuova():
    form = NewsForm()
    if form.validate_on_submit():
        articolo = News(
            titolo=form.titolo.data,
            contenuto=form.contenuto.data,
            sommario=form.sommario.data,
            categoria=form.categoria.data,
            tipo=form.tipo.data,
            pubblicata=form.pubblicata.data,
            data_pubblicazione=form.data_pubblicazione.data if form.data_pubblicazione.data else (datetime.now() if form.pubblicata.data else None),
            creato_da=current_user.id
        )

        if form.immagine.data:
            articolo.immagine = salva_immagine(form.immagine.data)

        db.session.add(articolo)
        db.session.commit()
        flash(f'News {articolo.titolo} creata con successo!', 'success')
        return redirect(url_for('news.dettaglio', id=articolo.id))

    return render_template('news/form.html', form=form, titolo='Nuova News')

@news_bp.route('/<int:id>/modifica', methods=['GET', 'POST'])
@login_required
def modifica(id):
    articolo = News.query.get_or_404(id)

    if not current_user.is_editor() and articolo.creato_da != current_user.id:
        flash('Non hai permesso di modificare questa news.', 'danger')
        return redirect(url_for('news.lista'))

    form = NewsForm(obj=articolo)
    if form.validate_on_submit():
        articolo.titolo = form.titolo.data
        articolo.contenuto = form.contenuto.data
        articolo.sommario = form.sommario.data
        articolo.categoria = form.categoria.data
        articolo.tipo = form.tipo.data
        articolo.pubblicata = form.pubblicata.data
        articolo.data_pubblicazione = form.data_pubblicazione.data if form.data_pubblicazione.data else (datetime.now() if form.pubblicata.data else None)

        if form.immagine.data:
            articolo.immagine = salva_immagine(form.immagine.data)

        db.session.commit()
        flash(f'News {articolo.titolo} aggiornata!', 'success')
        return redirect(url_for('news.dettaglio', id=articolo.id))

    return render_template('news/form.html', form=form, titolo='Modifica News', articolo=articolo)

@news_bp.route('/<int:id>/elimina')
@login_required
@editor_required
def elimina(id):
    articolo = News.query.get_or_404(id)
    titolo = articolo.titolo
    db.session.delete(articolo)
    db.session.commit()
    flash(f'News {titolo} eliminata.', 'success')
    return redirect(url_for('news.lista'))

@news_bp.route('/<int:id>/pubblica')
@login_required
@editor_required
def pubblica(id):
    articolo = News.query.get_or_404(id)
    articolo.pubblicata = True
    if not articolo.data_pubblicazione:
        articolo.data_pubblicazione = datetime.now()
    db.session.commit()
    flash(f'News {articolo.titolo} pubblicata!', 'success')
    return redirect(url_for('news.dettaglio', id=articolo.id))
