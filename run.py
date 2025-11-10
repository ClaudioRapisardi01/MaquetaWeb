from app import create_app, db
from app.models import User, Artista, Disco, Singolo, Evento, Servizio, Staff, Documento, News

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Artista': Artista,
        'Disco': Disco,
        'Singolo': Singolo,
        'Evento': Evento,
        'Servizio': Servizio,
        'Staff': Staff,
        'Documento': Documento,
        'News': News
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6000, debug=True)
