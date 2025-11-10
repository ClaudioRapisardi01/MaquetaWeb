from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import Artista, Disco, Singolo, Evento, News, Documento

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Statistiche per la dashboard
    stats = {
        'artisti': Artista.query.count(),
        'dischi': Disco.query.count(),
        'singoli': Singolo.query.count(),
        'eventi': Evento.query.count(),
        'documenti': Documento.query.count(),
        'news': News.query.filter_by(pubblicata=True).count()
    }

    # Ultimi elementi aggiunti
    ultimi_artisti = Artista.query.order_by(Artista.data_creazione.desc()).limit(5).all()
    ultimi_dischi = Disco.query.order_by(Disco.data_creazione.desc()).limit(5).all()
    prossimi_eventi = Evento.query.filter(Evento.data_inizio >= datetime.now()).order_by(Evento.data_inizio).limit(5).all()
    ultime_news = News.query.filter_by(pubblicata=True).order_by(News.data_pubblicazione.desc()).limit(5).all()

    return render_template('dashboard.html',
                         stats=stats,
                         ultimi_artisti=ultimi_artisti,
                         ultimi_dischi=ultimi_dischi,
                         prossimi_eventi=prossimi_eventi,
                         ultime_news=ultime_news)

from flask import redirect, url_for
from datetime import datetime
