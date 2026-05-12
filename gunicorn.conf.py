"""Configurazione gunicorn per MaquetaWeb.

Lanciato da start.sh, sostituisce il server di sviluppo Werkzeug.
Vantaggi:
  - Multi-worker: piu' request in parallelo (download di un GB non
    blocca piu' la pagina di un altro utente)
  - Niente reloader: cambi al codice richiedono restart esplicito
    (basta `./start.sh` di nuovo), che e' quello che vuoi in produzione
  - HTTPS nativo via --certfile/--keyfile
  - Timeout configurabili per upload/download lunghi
"""
import multiprocessing
import os

# Bind: ascolta su tutte le interfacce, porta 5000 (cambiarla per HTTPS).
# Quando si attiva TLS lo facciamo via env var SSL_ENABLED=1 + cert/key.
bind = '0.0.0.0:' + os.environ.get('PORT', '5000')

# Worker. Sync worker e` la scelta safe per la maggioranza dei casi.
# Per upload/download lunghi serve worker_class='sync' con timeout alti.
# Numero workers: regola di pollice = 2 * core + 1, capped per evitare
# overload.
workers = int(os.environ.get('WORKERS', max(2, multiprocessing.cpu_count() * 2 + 1)))
worker_class = 'sync'

# Timeout in secondi. Un download da 6GB a 8 MB/s impiega ~12 min = 720s.
# Mettiamo 1800s (30 min) per essere generosi senza tagliare downloads
# di file enormi.
timeout = int(os.environ.get('WORKER_TIMEOUT', '1800'))
graceful_timeout = 30
keepalive = 5

# Loglevel: info di base, ma stampiamo a stdout cosi` `./start.sh` mostra
# tutto live (e systemd journal-d li raccoglie quando in produzione).
loglevel = os.environ.get('LOGLEVEL', 'info')
accesslog = '-'   # stdout
errorlog = '-'    # stderr
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s %(M)sms'

# Limite massimo della request line (URL + headers). Default 4094, alziamo
# perche` query string lunghe (subpath profondi nel file manager) potrebbero
# saturare il default.
limit_request_line = 8190
limit_request_fields = 200
limit_request_field_size = 16380

# HTTPS: attivato da env. Per generare i cert vedi README sezione HTTPS.
_cert = os.environ.get('SSL_CERTFILE')
_key = os.environ.get('SSL_KEYFILE')
if _cert and _key and os.path.exists(_cert) and os.path.exists(_key):
    certfile = _cert
    keyfile = _key
    # SSL minimum version: TLS 1.2+
    ssl_version = 'TLSv1_2'

# Worker che lancia il modulo "app" e l'oggetto Flask "app".
# Equivalente di: gunicorn -c gunicorn.conf.py app:app
proc_name = 'maquetaweb'

# Hooks: log al pre-start cosi` nei log si vede chiaro l'inizio
def when_ready(server):
    server.log.info(
        f"MaquetaWeb pronta su {bind} - workers={workers} timeout={timeout}s"
        + (f" - HTTPS abilitato ({_cert})" if _cert and _key else "")
    )
