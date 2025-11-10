from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory
from flask_login import login_required, current_user
from app import db
from app.models import Documento
from app.forms import DocumentoForm
from werkzeug.utils import secure_filename
import os
from datetime import datetime

documenti_bp = Blueprint('documenti', __name__)

def salva_documento(file):
    if file:
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        filepath = os.path.join('app', 'static', 'uploads', 'documents', filename)
        file.save(filepath)
        return filename, os.path.getsize(filepath), file.content_type
    return None, None, None

@documenti_bp.route('/')
@login_required
def lista():
    page = request.args.get('page', 1, type=int)
    query = Documento.query

    # Gli admin vedono tutto, gli altri solo i propri documenti
    if not current_user.is_admin():
        query = query.filter_by(caricato_da=current_user.id)

    documenti = query.order_by(Documento.data_upload.desc()).paginate(page=page, per_page=15, error_out=False)
    return render_template('documenti/lista.html', documenti=documenti)

@documenti_bp.route('/<int:id>')
@login_required
def dettaglio(id):
    documento = Documento.query.get_or_404(id)

    # Controllo accesso
    if not current_user.is_admin() and documento.caricato_da != current_user.id:
        if documento.visibilita == 'privato':
            flash('Non hai permesso di visualizzare questo documento.', 'danger')
            return redirect(url_for('documenti.lista'))

    return render_template('documenti/dettaglio.html', documento=documento)

@documenti_bp.route('/nuovo', methods=['GET', 'POST'])
@login_required
def nuovo():
    form = DocumentoForm()
    if form.validate_on_submit():
        filename, dimensione, mime_type = salva_documento(form.file.data)

        if filename:
            documento = Documento(
                titolo=form.titolo.data,
                descrizione=form.descrizione.data,
                nome_file=filename,
                percorso_file=os.path.join('uploads', 'documents', filename),
                tipo=form.tipo.data,
                dimensione=dimensione,
                mime_type=mime_type,
                visibilita=form.visibilita.data,
                caricato_da=current_user.id
            )
            db.session.add(documento)
            db.session.commit()
            flash(f'Documento {documento.titolo} caricato con successo!', 'success')
            return redirect(url_for('documenti.dettaglio', id=documento.id))
        else:
            flash('Errore nel caricamento del file.', 'danger')

    return render_template('documenti/form.html', form=form, titolo='Nuovo Documento')

@documenti_bp.route('/<int:id>/download')
@login_required
def download(id):
    documento = Documento.query.get_or_404(id)

    # Controllo accesso
    if not current_user.is_admin() and documento.caricato_da != current_user.id:
        if documento.visibilita == 'privato':
            flash('Non hai permesso di scaricare questo documento.', 'danger')
            return redirect(url_for('documenti.lista'))

    directory = os.path.join('app', 'static', 'uploads', 'documents')
    return send_from_directory(directory, documento.nome_file, as_attachment=True)

@documenti_bp.route('/<int:id>/elimina')
@login_required
def elimina(id):
    documento = Documento.query.get_or_404(id)

    # Solo l'admin o chi ha caricato può eliminare
    if not current_user.is_admin() and documento.caricato_da != current_user.id:
        flash('Non hai permesso di eliminare questo documento.', 'danger')
        return redirect(url_for('documenti.lista'))

    # Elimina file fisico
    filepath = os.path.join('app', 'static', 'uploads', 'documents', documento.nome_file)
    if os.path.exists(filepath):
        os.remove(filepath)

    titolo = documento.titolo
    db.session.delete(documento)
    db.session.commit()
    flash(f'Documento {titolo} eliminato.', 'success')
    return redirect(url_for('documenti.lista'))
