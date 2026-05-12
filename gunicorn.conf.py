"""Configurazione gunicorn per MaquetaWeb.

Architettura: gunicorn sta DIETRO a nginx. Il TLS lo gestisce nginx col
suo certificato (Let's Encrypt o equivalente), gunicorn riceve traffico
in chiaro solo dal localhost di nginx.

Lo schema reale (https), l'host pubblico e l'IP del client sono
ricostruiti in Flask dall'header X-Forwarded-* via werkzeug ProxyFix
(vedi app.py).
"""
import multiprocessing
import os

# Bind: SOLO localhost. Cosi` la porta gunicorn non e` raggiungibile da
# fuori la macchina; tutto il traffico esterno DEVE passare da nginx.
# Per override esplicito (es. test locale via LAN) settare BIND_HOST=0.0.0.0
_host = os.environ.get('BIND_HOST', '127.0.0.1')
_port = os.environ.get('PORT', '5000')
bind = f'{_host}:{_port}'

# Worker. Regola di pollice: 2 * core + 1.
workers = int(os.environ.get('WORKERS', max(2, multiprocessing.cpu_count() * 2 + 1)))
worker_class = 'sync'

# Timeout in secondi. Un download da 6GB a 8 MB/s impiega ~12 min = 720s.
# Mettiamo 1800s (30 min) per essere generosi senza tagliare downloads
# di file enormi. Allinea questo valore col `proxy_read_timeout` in nginx.
timeout = int(os.environ.get('WORKER_TIMEOUT', '1800'))
graceful_timeout = 30
keepalive = 5

# Loglevel: info di base. Output su stdout/stderr cosi` `./start.sh` mostra
# tutto live, e systemd journal-d li raccoglie quando in produzione.
loglevel = os.environ.get('LOGLEVEL', 'info')
accesslog = '-'   # stdout
errorlog = '-'    # stderr
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s %(M)sms'

# Limite massimo della request line e dei field. Default Werkzeug ok, ma
# alziamo per URL/query string profondi del file manager.
limit_request_line = 8190
limit_request_fields = 200
limit_request_field_size = 16380

# Trust del proxy davanti: dichiariamo a gunicorn quale IP e` il nostro
# nginx (di default localhost). Cosi` gunicorn accetta gli header
# X-Forwarded-* solo se vengono da quell'IP.
forwarded_allow_ips = os.environ.get('FORWARDED_ALLOW_IPS', '127.0.0.1')

proc_name = 'maquetaweb'


def when_ready(server):
    server.log.info(
        f"MaquetaWeb pronta su http://{bind} (interno) - "
        f"workers={workers} timeout={timeout}s"
    )
    server.log.info(
        "Configura nginx come reverse proxy davanti: vedi docs/nginx.conf.sample"
    )
